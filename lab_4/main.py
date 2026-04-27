import sys
import numpy as np
from itertools import combinations
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QHeaderView, QMessageBox, QGroupBox, QGridLayout,
    QSplitter, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from smo import simulate_smo


FACTOR_RANGES = {
    "λ1": (0.3, 0.4),
    "λ2": (0.2, 0.4),
    "μ": (2.0, 2.6),
    "r": (2.4, 4.0)
}
FACTOR_NAMES = list(FACTOR_RANGES.keys())
NUM_FACTORS = len(FACTOR_NAMES)

# Параметры ОЦКП
# Для 4 факторов: m = 4, N = 2^m + 2m + 2 = 26
NC = 2  # число центральных точек

# Звездное плечо для ОЦКП
ALPHA = 2.0 # α = (2^(m/4)) для m=4: α = 2^(1) = 2

MAX_REQUESTS = 1000

RESULT_COLUMNS = [
    "№", "z1(λ1)", "z2(λ2)", "z3(μ)", "z4(r)",
    "y1", "y1_pred", "Δy1",
    "y2", "y2_pred", "Δy2"
]

def create_ccd_matrix(num_factors, alpha, nc):
    """
    Создает матрицу планирования ОЦКП для num_factors факторов.
    Возвращает матрицу в кодированных переменных (-α, -1, 0, 1, α)
    """
    rows = []
    
    # 1. Ядро плана (ПФЭ 2^m) - точки в вершинах куба (±1)
    for i in range(2 ** num_factors):
        x = [-1 if (i >> k) % 2 == 0 else 1 for k in range(num_factors)]
        rows.append(x)
    
    # 2. Звездные точки (на осях на расстоянии ±α)
    for j in range(num_factors):
        x = [0] * num_factors
        x[j] = alpha
        rows.append(x)
        
        x = [0] * num_factors
        x[j] = -alpha
        rows.append(x)
    
    # 3. Центральные точки
    for _ in range(nc):
        rows.append([0] * num_factors)
    
    return np.array(rows)

def build_design_matrix_with_interactions(x_matrix, include_quadratic=True):
    """
    Строит расширенную матрицу планирования:
    [1, x1, x2, ..., xm, x1², x2², ..., x1x2, x1x3, ...]
    """
    n_rows = x_matrix.shape[0]
    m = x_matrix.shape[1]
    
    # Список для хранения столбцов
    cols = [np.ones(n_rows)]  # свободный член
    
    # Линейные члены
    for j in range(m):
        cols.append(x_matrix[:, j])
    
    # Квадратичные члены (с центрированием для ортогональности)
    if include_quadratic:
        # Для ОЦКП используем центрированные квадраты: (xj² - S)
        S = (2 ** m + 2 * ALPHA ** 2) / (2 ** m + 2 * m + NC)
        for j in range(m):
            cols.append(x_matrix[:, j] ** 2 - S)
    
    # Члены взаимодействия (x_i * x_j, i < j)
    for i in range(m):
        for j in range(i + 1, m):
            cols.append(x_matrix[:, i] * x_matrix[:, j])
    
    return np.column_stack(cols)

def calculate_regression_coefficients(design_matrix, response):
    """ Вычисляет коэффициенты регрессии методом наименьших квадратов """
    return np.linalg.lstsq(design_matrix, response, rcond=None)[0]

def predict(coefficients, design_row):
    """ Предсказание значения по коэффициентам и строке дизайн-матрицы """
    return sum(coefficients[i] * design_row[i] for i in range(len(coefficients)))

def natural_to_coded(natural_values, mid_points, half_ranges):
    """Перевод натуральных значений в кодированные"""
    return [(natural_values[i] - mid_points[i]) / half_ranges[i] for i in range(len(natural_values))]

def coded_to_natural(coded_values, mid_points, half_ranges):
    """Перевод кодированных значений в натуральные"""
    return [mid_points[i] + coded_values[i] * half_ranges[i] for i in range(len(coded_values))]

def get_mid_points_and_ranges(center_values):
    """Получает mid_points из центральных значений и half_ranges из FACTOR_RANGES"""
    mid_points = center_values
    half_ranges = [(FACTOR_RANGES[name][1] - FACTOR_RANGES[name][0]) / 2 for name in FACTOR_NAMES]
    return mid_points, half_ranges

# (строка)
def build_equation_normalized(coefficients, factor_names, include_quadratic=True):
    """Строит уравнение в нормированных координатах"""
    m = len(factor_names)
    terms = ["1"] + [f"z{i+1}" for i in range(m)]
    
    if include_quadratic:
        terms += [f"z{i+1}²" for i in range(m)]
    
    # Добавляем взаимодействия
    terms += [f"z{i+1}z{j+1}" for i in range(m) for j in range(i+1, m)]
    
    parts = []
    for i, coef in enumerate(coefficients):
        if i == 0:
            parts.append(f"{coef:.6f}")
        else:
            if abs(coef) > 1e-10:
                sign = "+" if coef >= 0 else "-"
                parts.append(f"{sign} {abs(coef):.6f}·{terms[i]}")
    
    return "ŷ = " + " ".join(parts)

# (строка)
def build_equation_natural(coefficients, factor_names, mid_points, half_ranges, include_quadratic=True):
    """Строит уравнение в натуральных координатах (преобразование из нормированного)"""
    m = len(factor_names)
    
    # Генерация членов в том же порядке, что и в design_matrix
    linear_terms = [f"x{i+1}" for i in range(m)]
    quadratic_terms = [f"x{i+1}²" for i in range(m)] if include_quadratic else []
    interaction_terms = [f"x{i+1}x{j+1}" for i in range(m) for j in range(i+1, m)]
    
    all_terms = ["1"] + linear_terms + quadratic_terms + interaction_terms
    
    # Вычисляем новые коэффициенты
    new_coefficients = [0] * len(coefficients)
    new_coefficients[0] = coefficients[0]
    
    # Свободный член преобразуется с учетом центрирования
    for i in range(m):
        new_coefficients[0] -= coefficients[i + 1] * mid_points[i] / half_ranges[i]
    
    if include_quadratic:
        S = (2 ** m + 2 * ALPHA ** 2) / (2 ** m + 2 * m + NC)
        for i in range(m):
            idx = 1 + m + i
            new_coefficients[idx] = coefficients[idx] / (half_ranges[i] ** 2)
            new_coefficients[0] += coefficients[idx] * (mid_points[i] ** 2 / half_ranges[i] ** 2 - S)
    
    # Линейные члены
    for i in range(m):
        idx = 1 + i
        new_coefficients[idx] = coefficients[idx] / half_ranges[i]
    
    # Взаимодействия
    interaction_idx = 1 + m
    if include_quadratic:
        interaction_idx += m
    
    for i in range(m):
        for j in range(i+1, m):
            new_coefficients[interaction_idx] = coefficients[interaction_idx] / (half_ranges[i] * half_ranges[j])
            interaction_idx += 1
    
    # Формируем строку уравнения
    parts = []
    for i, coef in enumerate(new_coefficients):
        term = all_terms[i]
        if term == "1":
            parts.append(f"{coef:.6f}")
        else:
            if abs(coef) > 1e-10:
                sign = "+" if coef >= 0 else "-"
                parts.append(f"{sign} {abs(coef):.6f}·{term}")
    
    return "ŷ = " + " ".join(parts)


def run_simulation_for_point(natural_values, max_requests):
    lam1, lam2, mu, r = natural_values
    _, _, avg_wait1, avg_wait2, _, _ = simulate_smo(lam1, lam2, mu, r, max_requests)
    return avg_wait1, avg_wait2

def run_full_experiment(ccd_matrix, mid_points, half_ranges, max_requests, progress_callback=None):
    """ Выполняет эксперимент для всех точек матрицы ОЦКП """
    n_rows = ccd_matrix.shape[0]
    y1_responses = []
    y2_responses = []
    
    for i, coded_row in enumerate(ccd_matrix):
        natural = coded_to_natural(coded_row, mid_points, half_ranges)
        y1, y2 = run_simulation_for_point(natural, max_requests)
        y1_responses.append(y1)
        y2_responses.append(y2)
        
        if progress_callback:
            progress_callback(i + 1, n_rows)
    
    # Строим расширенную дизайн-матрицу
    design_matrix = build_design_matrix_with_interactions(ccd_matrix, include_quadratic=True)
    
    # Вычисляем коэффициенты
    coeffs_y1 = calculate_regression_coefficients(design_matrix, y1_responses)
    coeffs_y2 = calculate_regression_coefficients(design_matrix, y2_responses)
    
    # Вычисляем предсказания
    y1_pred = [predict(coeffs_y1, design_matrix[i]) for i in range(n_rows)]
    y2_pred = [predict(coeffs_y2, design_matrix[i]) for i in range(n_rows)]
    
    return {
        'y1_actual': y1_responses,
        'y2_actual': y2_responses,
        'y1_pred': y1_pred,
        'y2_pred': y2_pred,
        'coeffs_y1': coeffs_y1,
        'coeffs_y2': coeffs_y2,
        'ccd_matrix': ccd_matrix
    }


class CalculationThread(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, center_values):
        super().__init__()
        self.center_values = center_values
    
    def run(self):
        try:
            mid_points, half_ranges = get_mid_points_and_ranges(self.center_values)
            ccd_matrix = create_ccd_matrix(NUM_FACTORS, ALPHA, NC)
            def update_progress(current, total):
                self.progress.emit(current, total)

            results = run_full_experiment(ccd_matrix, mid_points, half_ranges, MAX_REQUESTS, update_progress)
            results['mid_points'] = mid_points
            results['half_ranges'] = half_ranges
            results['ccd_matrix'] = ccd_matrix
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Имитационная модель СМО (дисциплина обслуживания LIFO)")
        self.setGeometry(0, 0, 1200, 800)
        self.calculation_thread = None
        self.results = None
        self._setup_ui()
    
    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        input_group = QGroupBox("Параметры эксперимента")
        input_layout = QGridLayout(input_group)
        
        self.factor_inputs = {}
        row = 0
        for name, (min_val, max_val) in FACTOR_RANGES.items():
            label_text = f"{name}  [{min_val} - {max_val}]"
            if 'λ' in name:
                label_text = f"(Закон распределения Рэлея) {label_text}"
            elif name == 'μ':
                label_text = f"(Равномерный закон распределения) {label_text}"
            else:
                label_text = f"(Равномерный закон распределения) {label_text}"
            
            label = QLabel(label_text)
            input_layout.addWidget(label, row, 0)
            
            default_value = (min_val + max_val) / 2
            line_edit = QLineEdit(str(default_value))
            input_layout.addWidget(line_edit, row, 1)
            
            self.factor_inputs[name] = line_edit
            row += 1
        
        self.calc_button = QPushButton("Выполнить ОЦКП эксперимент")
        self.calc_button.clicked.connect(self._on_calculate)
        input_layout.addWidget(self.calc_button, row, 0, 1, 2)
        
        main_layout.addWidget(input_group)
        
        # === Прогресс бар ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # === Разделитель ===
        splitter = QSplitter(Qt.Vertical)
        
        # Таблица результатов
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(len(RESULT_COLUMNS))
        self.results_table.setHorizontalHeaderLabels(RESULT_COLUMNS)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.results_table.setAlternatingRowColors(True)
        
        # Настройка ширины столбцов
        self.results_table.setColumnWidth(0, 50)   # №
        for i in range(NUM_FACTORS):
            self.results_table.setColumnWidth(i + 1, 80)  # z1..z4
        
        table_layout.addWidget(self.results_table)
        splitter.addWidget(table_container)
        
        # Текстовое поле для уравнений
        equations_container = QWidget()
        equations_layout = QVBoxLayout(equations_container)
        equations_layout.setContentsMargins(0, 0, 0, 0)
        
        equations_label = QLabel("Регрессионные уравнения (ОЦКП, модель 2-го порядка):")
        equations_layout.addWidget(equations_label)
        
        self.equations_text = QTextEdit()
        self.equations_text.setReadOnly(True)
        self.equations_text.setFontFamily("Courier New")
        self.equations_text.setFontPointSize(10)
        equations_layout.addWidget(self.equations_text)
        
        splitter.addWidget(equations_container)
        splitter.setSizes([500, 400])
        
        main_layout.addWidget(splitter)
    
    def _read_center_values(self):
        """Читает значения центральной точки"""
        return [float(self.factor_inputs[name].text()) for name in FACTOR_NAMES]
    
    def _populate_results_table(self, results):
        """Заполняет таблицу результатов"""
        ccd_matrix = results['ccd_matrix']
        y1_actual = results['y1_actual']
        y2_actual = results['y2_actual']
        y1_pred = results['y1_pred']
        y2_pred = results['y2_pred']
        
        self.results_table.setRowCount(len(y1_actual))
        
        for row_idx in range(len(y1_actual)):
            # Номер эксперимента
            self.results_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))
            
            # Значения факторов (кодированные)
            for col_idx, val in enumerate(ccd_matrix[row_idx]):
                item = QTableWidgetItem(f"{val:+.3f}")
                item.setTextAlignment(Qt.AlignCenter)
                self.results_table.setItem(row_idx, col_idx + 1, item)
            
            # y1, y1_pred, Δy1
            col = NUM_FACTORS + 1
            self.results_table.setItem(row_idx, col, QTableWidgetItem(f"{y1_actual[row_idx]:.6f}"))
            self.results_table.setItem(row_idx, col + 1, QTableWidgetItem(f"{y1_pred[row_idx]:.6f}"))
            self.results_table.setItem(row_idx, col + 2, QTableWidgetItem(f"{abs(y1_actual[row_idx] - y1_pred[row_idx]):.6f}"))
            
            # y2, y2_pred, Δy2
            self.results_table.setItem(row_idx, col + 3, QTableWidgetItem(f"{y2_actual[row_idx]:.6f}"))
            self.results_table.setItem(row_idx, col + 4, QTableWidgetItem(f"{y2_pred[row_idx]:.6f}"))
            self.results_table.setItem(row_idx, col + 5, QTableWidgetItem(f"{abs(y2_actual[row_idx] - y2_pred[row_idx]):.6f}"))
    
    def _display_equations(self, results):
        """Отображает уравнения регрессии"""
        coeffs_y1 = results['coeffs_y1']
        coeffs_y2 = results['coeffs_y2']
        mid_points = results['mid_points']
        half_ranges = results['half_ranges']
        
        equations_text = []
        
        line = "═" * 70
        
        # y1 уравнения
        equations_text.append(line)
        equations_text.append("РЕЗУЛЬТАТЫ ДЛЯ y1 (среднее время ожидания заявок типа 1)")
        equations_text.append(line)
        equations_text.append("")
        
        equations_text.append("Уравнение в КОДИРОВАННЫХ координатах (z₁, z₂, z₃, z₄):")
        equations_text.append("-" * 70)
        eq_y1_norm = build_equation_normalized(coeffs_y1, FACTOR_NAMES, include_quadratic=True)
        equations_text.append(eq_y1_norm)
        equations_text.append("")
        
        equations_text.append("Уравнение в НАТУРАЛЬНЫХ координатах (λ₁, λ₂, μ, r):")
        equations_text.append("-" * 70)
        eq_y1_nat = build_equation_natural(coeffs_y1, FACTOR_NAMES, mid_points, half_ranges, include_quadratic=True)
        equations_text.append(eq_y1_nat)
        equations_text.append("")
        
        # y2 уравнения
        equations_text.append(line)
        equations_text.append("РЕЗУЛЬТАТЫ ДЛЯ y2 (среднее время ожидания заявок типа 2)")
        equations_text.append(line)
        equations_text.append("")
        
        equations_text.append("Уравнение в КОДИРОВАННЫХ координатах (z₁, z₂, z₃, z₄):")
        equations_text.append("-" * 70)
        eq_y2_norm = build_equation_normalized(coeffs_y2, FACTOR_NAMES, include_quadratic=True)
        equations_text.append(eq_y2_norm)
        equations_text.append("")
        
        equations_text.append("Уравнение в НАТУРАЛЬНЫХ координатах (λ₁, λ₂, μ, r):")
        equations_text.append("-" * 70)
        eq_y2_nat = build_equation_natural(coeffs_y2, FACTOR_NAMES, mid_points, half_ranges, include_quadratic=True)
        equations_text.append(eq_y2_nat)
        equations_text.append("")
        
        # Информация о плане
        equations_text.append(line)
        equations_text.append("ПАРАМЕТРЫ ОЦКП")
        equations_text.append(line)
        equations_text.append(f"Число факторов (m): {NUM_FACTORS}")
        equations_text.append(f"Число опытов ядра (2^m): {2 ** NUM_FACTORS}")
        equations_text.append(f"Число звездных точек (2m): {2 * NUM_FACTORS}")
        equations_text.append(f"Число центральных точек (nc): {NC}")
        equations_text.append(f"Общее число опытов (N): {2 ** NUM_FACTORS + 2 * NUM_FACTORS + NC}")
        equations_text.append(f"Звездное плечо (α): {ALPHA}")
        equations_text.append("")
        equations_text.append("Центральная точка (натуральные значения):")
        for i, name in enumerate(FACTOR_NAMES):
            equations_text.append(f"  {name} = {mid_points[i]:.4f}")
        equations_text.append("")
        equations_text.append("Интервалы варьирования (Δ):")
        for i, name in enumerate(FACTOR_NAMES):
            equations_text.append(f"  {name} = ±{half_ranges[i]:.4f}")
        
        self.equations_text.setPlainText("\n".join(equations_text))
    
    def _on_calculate(self):
        """Обработчик нажатия кнопки"""
        if self.calculation_thread and self.calculation_thread.isRunning():
            QMessageBox.warning(self, "Предупреждение", "Расчет уже выполняется...")
            return
        
        try:
            center_values = self._read_center_values()
            
            # Проверка диапазонов
            for i, name in enumerate(FACTOR_NAMES):
                min_val, max_val = FACTOR_RANGES[name]
                if not (min_val <= center_values[i] <= max_val):
                    QMessageBox.warning(
                        self, "Предупреждение",
                        f"Значение {name}={center_values[i]} выходит за пределы [{min_val}, {max_val}]"
                    )
                    return
            
            # Блокируем кнопку и показываем прогресс
            self.calc_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Запускаем поток вычислений
            self.calculation_thread = CalculationThread(center_values)
            self.calculation_thread.progress.connect(self._on_progress)
            self.calculation_thread.finished.connect(self._on_finished)
            self.calculation_thread.error.connect(self._on_error)
            self.calculation_thread.start()
            
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка ввода", f"Некорректное числовое значение: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка: {e}")
    
    def _on_progress(self, current, total):
        """Обновление прогресса"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"Выполняется эксперимент... {current}/{total} опытов")
    
    def _on_finished(self, results):
        """Завершение расчета"""
        self.results = results
        self._populate_results_table(results)
        self._display_equations(results)
        
        self.calc_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        QMessageBox.information(
            self, "Завершено",
            f"Эксперимент успешно выполнен!\n"
            f"Всего опытов: {len(results['y1_actual'])}"
        )
    
    def _on_error(self, error_msg):
        """Обработка ошибки"""
        self.calc_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Ошибка", f"Ошибка при расчете:\n{error_msg}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()