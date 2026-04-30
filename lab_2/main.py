import sys
import numpy as np
from itertools import combinations
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QHeaderView, QMessageBox, QGroupBox, QGridLayout,
    QScrollArea, QSplitter
)
from PyQt5.QtCore import Qt
from smo import simulate_smo


# Область определения факторов
FACTOR_RANGES = {
    "λ1": (0.3, 0.4),
    "λ2": (0.2, 0.4),
    "μ": (2, 2.6),
    "r": (2.4, 4)
}
FACTOR_NAMES = list(FACTOR_RANGES.keys())
NUM_FACTORS = len(FACTOR_NAMES)
RESULT_COLUMNS = [
    "№", "λ1", "λ2", "μ", "r", 
    "y1", "y1_lin", "Δy1_lin%", "y1_nlin", # "Δy1_nlin%",
    "y2", "y2_lin", "Δy2_lin%", "y2_nlin", # "Δy2_nlin%"
]
MAX_REQUESTS = 1000

""" Полная матрица планирования 2^n: 1, x1, x2, ..., xn, x1*x2, x1*x3, ..., x(n-1)*xn, x1*x2*x3, ...]"""
def generate_full_factorial_matrix(num_factors):
    num_combinations = 2 ** num_factors
    matrix = []
    
    for i in range(num_combinations):
        # Кодируем номер строки в бинарный вектор (-1, 1)
        factor_levels = [-1 if (i >> k) % 2 == 0 else 1 for k in range(num_factors)]
        row = [1] + factor_levels
        for interaction_order in range(2, num_factors + 1):
            for factor_indices in combinations(range(num_factors), interaction_order):
                interaction_value = 1
                for idx in factor_indices:
                    interaction_value *= factor_levels[idx]
                row.append(interaction_value)
        matrix.append(row)
    
    return matrix

""" Вычисляет линейные коэффициенты регрессии: Использует только первые NUM_FACTORS + 1 столбцов матрицы планирования. """
def calculate_linear_coefficients(design_matrix, response_values):
    num_experiments = len(design_matrix)
    num_coefficients = NUM_FACTORS + 1  
    
    coefficients = []
    for j in range(num_coefficients):
        coef = sum(design_matrix[i][j] * response_values[i] for i in range(num_experiments)) / num_experiments
        coefficients.append(coef)
    
    return coefficients

""" Вычисляет коэффициенты регрессии методом наименьших квадратов: a_j = (1/N) * Σ(y_i * x_ij) """
def calculate_regression_coefficients(design_matrix, response_values):
    num_experiments = len(design_matrix)
    num_coefficients = len(design_matrix[0])
    
    coefficients = []
    for j in range(num_coefficients):
        coef = sum(design_matrix[i][j] * response_values[i] for i in range(num_experiments)) / num_experiments
        coefficients.append(coef)
    
    return coefficients

""" Линейная модель: y = a0 + a1*x1 + a2*x2 + ... + an*xn"""
def predict_linear(coefficients, factor_levels):
    return sum(coefficients[j] * factor_levels[j] for j in range(len(coefficients)))

""" Полная модель со всеми взаимодействиями. """
def predict_full(coefficients, factor_levels):
    return sum(coefficients[j] * factor_levels[j] for j in range(len(factor_levels)))

""" Преобразует нормированные значения (-1, 1) в натуральные. """
def convert_normalized_to_natural(normalized_values, mid_points, half_ranges):
    return [mid_points[i] + normalized_values[i] * half_ranges[i] for i in range(len(normalized_values))]

""" Строит линейное уравнение в нормированных координатах (строка)"""
def build_regression_equation_normalized_linear(coefficients, factor_names):
    equation_parts = [f"{coefficients[0]:.4f}"]  # b0
    
    for i, name in enumerate(factor_names):
        coef = coefficients[i + 1]
        if abs(coef) > 1e-10:
            if coef >= 0:
                equation_parts.append(f"+ {coef:.4f}·{name}")
            else:
                equation_parts.append(f"- {abs(coef):.4f}·{name}")
    
    return "y = " + " ".join(equation_parts)

""" Строит линейное уравнение в натуральных координатах  (строка)"""
def build_regression_equation_natural_linear(coefficients, factor_names, mid_points, half_ranges):
    n = len(factor_names)
    
    # Преобразование свободного члена
    constant_term = coefficients[0]
    for i in range(n):
        constant_term += coefficients[i + 1] * (-mid_points[i] / half_ranges[i])
    
    equation_parts = [f"{constant_term:.4f}"]
    
    # Линейные члены
    for i, name in enumerate(factor_names):
        linear_coef = coefficients[i + 1] / half_ranges[i]
        if abs(linear_coef) > 1e-10:
            if linear_coef >= 0:
                equation_parts.append(f"+ {linear_coef:.4f}·{name}")
            else:
                equation_parts.append(f"- {abs(linear_coef):.4f}·{name}")
    
    return "y = " + " ".join(equation_parts)

""" Строит полное уравнение в нормированных координатах  (строка)"""
def build_regression_equation_normalized_full(coefficients, factor_names):
    n = len(factor_names)
    terms = ["1"]  # свободный член
    
    # Добавляем члены всех порядков (от 1 до n)
    for order in range(1, n + 1):
        for indices in combinations(range(n), order):
            term = "·".join(factor_names[i] for i in indices)
            terms.append(term)
    
    # Формируем уравнение
    equation_parts = []
    for i, term in enumerate(terms):
        coef = coefficients[i]
        if term == "1":
            equation_parts.append(f"{coef:.4f}")
        else:
            if coef >= 0 and i > 0:
                equation_parts.append(f"+ {coef:.4f}·{term}")
            elif coef < 0:
                equation_parts.append(f"- {abs(coef):.4f}·{term}")
            else:
                equation_parts.append(f"{coef:.4f}·{term}")
    
    if equation_parts:
        result = "y = " + " ".join(equation_parts).lstrip("+ ")
    else:
        result = "y = 0"
    return result

""" Строит полное уравнение в натуральных координатах  (строка)"""
def build_regression_equation_natural_full(coefficients, factor_names, mid_points, half_ranges):
    n = len(factor_names)
    
    # Генерируем все члены в том же порядке, что и в design_matrix
    terms = ["1"]
    for order in range(1, n + 1):
        for indices in combinations(range(n), order):
            term = "·".join(factor_names[i] for i in indices)
            terms.append(term)
    
    # Вычисляем новый свободный член
    new_constant = coefficients[0]
    for idx in range(1, len(terms)):
        indices = []
        # Находим индексы для этого члена
        term = terms[idx]
        if term != "1":
            # Разбираем терм, чтобы получить индексы (упрощенный способ)
            for i, name in enumerate(factor_names):
                if name in term.split("·"):
                    indices.append(i)
        
        if indices:  # если есть индексы
            coef = coefficients[idx]
            contribution = coef
            for i in indices:
                contribution *= (-mid_points[i] / half_ranges[i])
            new_constant += contribution
    
    # Формируем строку уравнения
    equation_parts = [f"{new_constant:.6f}"]
    
    # Добавляем все члены
    for idx in range(1, len(terms)):
        term = terms[idx]
        indices = []
        for i, name in enumerate(factor_names):
            if name in term.split("·"):
                indices.append(i)
        
        if indices:
            coef = coefficients[idx]
            # Преобразуем коэффициент
            divisor = 1.0
            for i in indices:
                divisor *= half_ranges[i]
            transformed_coef = coef / divisor
            
            if abs(transformed_coef) > 1e-10:
                if transformed_coef >= 0:
                    equation_parts.append(f"+ {transformed_coef:.6f}·{term}")
                else:
                    equation_parts.append(f"- {abs(transformed_coef):.6f}·{term}")
    
    return "y = " + " ".join(equation_parts)

""" Возвращает кортеж (avg_wait1, avg_wait2). """
def run_simulation(lam1, lam2, mu, rang, max_requests):
    _, _, avg_wait1, avg_wait2, _, _ = simulate_smo(lam1, lam2, mu, rang, max_requests)  
    return avg_wait1, avg_wait2

"""
mid_points - натуральные значение нулевых уровней каждого фактора
half_ranges - половина интервала вариарованя для каждого фактора
design_matrix - полная матрица планирования (значения -1, +1 и их произведения)
"""
def calculate_experiment_results(mid_points, half_ranges, design_matrix):
    natural_values = []
    for row in design_matrix:
        normalized = row[1:NUM_FACTORS + 1]  # x1, x2, x3, x4 (без 1 в начале)
        natural = convert_normalized_to_natural(normalized, mid_points, half_ranges)
        natural_values.append(natural)
    
    y1_responses = []   # среднее время ожидания для заявок типа 1
    y2_responses = []   # среднее время ожидания для заявок типа 2
    for values in natural_values:
        lam1, lam2, mu, rang = values
        avg_wait1, avg_wait2 = run_simulation(lam1, lam2, mu, rang, MAX_REQUESTS)
        y1_responses.append(avg_wait1)
        y2_responses.append(avg_wait2)

    # Вычисляем коэффициенты для полной модели 
    a1_full = calculate_regression_coefficients(design_matrix, y1_responses)
    a2_full = calculate_regression_coefficients(design_matrix, y2_responses)
    # Вычисляем коэффициенты для не полной модели 
    a1_linear = calculate_linear_coefficients(design_matrix, y1_responses)
    a2_linear = calculate_linear_coefficients(design_matrix, y2_responses)
    
    table_data = [] # Таблица результатов
    for i, row in enumerate(design_matrix):
        y1_actual = y1_responses[i] # Реальное значение из симуляции
        y2_actual = y2_responses[i]
        
        y1_linear = predict_linear(a1_linear, row)     # Только линейные члены
        y1_full = predict_full(a1_full, row)         # Со всеми взаимодействиями
        y2_linear = predict_linear(a2_linear, row)
        y2_full = predict_full(a2_full, row)
        
        # Вычисляем процент отклонения
        delta_y1_lin_percent = 0.0 if y1_actual == 0 else (abs(y1_actual - y1_linear) / abs(y1_actual)) * 100
        # delta_y1_nlin_percent = 0.0 if y1_actual == 0 else (abs(y1_actual - y1_full) / abs(y1_actual)) * 100
        delta_y2_lin_percent = 0.0 if y2_actual == 0 else (abs(y2_actual - y2_linear) / abs(y2_actual)) * 100
        # delta_y2_nlin_percent = 0.0 if y2_actual == 0 else (abs(y2_actual - y2_full) / abs(y2_actual)) * 100
        
        table_data.append({
            'num': i + 1,
            'factors': row[1:NUM_FACTORS + 1],
            'y1': y1_actual,
            'y1_lin': y1_linear,
            'y1_lin_percent': delta_y1_lin_percent,
            'y1_nlin': y1_full,
            # 'y1_nlin_percent': delta_y1_nlin_percent,
            'y2': y2_actual,
            'y2_lin': y2_linear,
            'y2_lin_percent': delta_y2_lin_percent,
            'y2_nlin': y2_full,
            # 'y2_nlin_percent': delta_y2_nlin_percent
        })
    
    return {
        'table_data': table_data,
        'coefficients_y1_linear': a1_linear,
        'coefficients_y1_full': a1_full,
        'coefficients_y2_linear': a2_linear,
        'coefficients_y2_full': a2_full
    }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Имитационная модель СМО (дисциплина обслуживания LIFO)")
        self.setGeometry(0, 0, 1200, 800)
        
        self.design_matrix = generate_full_factorial_matrix(NUM_FACTORS)
        
        self._setup_ui()
    
    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        input_group = QGroupBox("Параметры эксперимента (центральная точка)")
        input_layout = QGridLayout(input_group)
        
        self.factor_inputs = {}
        for i, (name, (min_val, max_val)) in enumerate(FACTOR_RANGES.items()):
            text_before = ""
            if 'λ' in name:
                text_before = f"(Закон распределения Рэлея)\t\t" 
            else:
                text_before = f"(Равномерный закон распределения)\t"
            label = QLabel(f"{text_before}{name} \t[{min_val} - {max_val}]:   ")
            input_layout.addWidget(label, i, 0)
            
            default_value = (min_val + max_val) / 2
            line_edit = QLineEdit(str(default_value))
            # line_edit.setFixedWidth(200)
            input_layout.addWidget(line_edit, i, 1)
            
            self.factor_inputs[name] = line_edit
        
        self.calc_button = QPushButton("Вычислить полный эксперимент")
        # self.calc_button.setFixedHeight(40)
        self.calc_button.clicked.connect(self._on_calculate)
        input_layout.addWidget(self.calc_button, NUM_FACTORS, 0, 1, 2)
        
        main_layout.addWidget(input_group)
        
        splitter = QSplitter(Qt.Vertical)

        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(len(RESULT_COLUMNS))
        self.results_table.setHorizontalHeaderLabels(RESULT_COLUMNS)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Настройка ширины столбцов
        self.results_table.setColumnWidth(0, 50)  # №
        for i in range(1, NUM_FACTORS+1):  # Факторы
            self.results_table.setColumnWidth(i, 60)
        
        table_layout.addWidget(self.results_table)
        splitter.addWidget(table_container)
        
        # === Текстовое поле для уравнений ===
        equations_container = QWidget()
        equations_layout = QVBoxLayout(equations_container)
        equations_layout.setContentsMargins(0, 0, 0, 0)
        
        equations_label = QLabel("Регрессионные уравнения:")
        equations_layout.addWidget(equations_label)
        
        self.equations_text = QTextEdit()
        self.equations_text.setReadOnly(True)
        self.equations_text.setFontFamily("Consolas")
        self.equations_text.setFontPointSize(10)
        equations_layout.addWidget(self.equations_text)
        
        splitter.addWidget(equations_container)
        splitter.setSizes([500, 500])
        
        main_layout.addWidget(splitter)
    
    def _read_input_values(self):
        mid_points = []
        for name in FACTOR_NAMES:
            print(self.factor_inputs[name].text())
            value = float(self.factor_inputs[name].text())
            mid_points.append(value)
        return mid_points
    
    def _calculate_half_ranges(self):
        """Вычисляет половины интервалов варьирования."""
        half_ranges = []
        for name in FACTOR_NAMES:
            min_val, max_val = FACTOR_RANGES[name]
            half_ranges.append((max_val - min_val) / 2)
        return half_ranges
    
    def _populate_results_table(self, table_data):
        self.results_table.setRowCount(len(table_data))
        
        for row_idx, row_data in enumerate(table_data):
            # Номер эксперимента
            self.results_table.setItem(row_idx, 0, QTableWidgetItem(str(row_data['num'])))
            
            # Значения факторов
            for i, factor_val in enumerate(row_data['factors']):
                item = QTableWidgetItem(f"{factor_val:+.0f}")
                item.setTextAlignment(Qt.AlignCenter)
                self.results_table.setItem(row_idx, i + 1, item)
            
            # Значения y1
            col = NUM_FACTORS + 1
            
            # y1 actual
            item = QTableWidgetItem(f"{row_data['y1']:.4e}")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.results_table.setItem(row_idx, col, item)
            col += 1
            
            # y1_lin
            item = QTableWidgetItem(f"{row_data['y1_lin']:.4e}")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.results_table.setItem(row_idx, col, item)
            col += 1
            
            # Δy1_lin%
            item = QTableWidgetItem(f"{row_data['y1_lin_percent']:.2f}%")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.results_table.setItem(row_idx, col, item)
            col += 1
            
            # y1_nlin
            item = QTableWidgetItem(f"{row_data['y1_nlin']:.4e}")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.results_table.setItem(row_idx, col, item)
            col += 1
            
            # Δy1_nlin%
            # item = QTableWidgetItem(f"{row_data['y1_nlin_percent']:.2f}%")
            # item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            # self.results_table.setItem(row_idx, col, item)
            # col += 1
            
            # y2 actual
            item = QTableWidgetItem(f"{row_data['y2']:.4e}")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.results_table.setItem(row_idx, col, item)
            col += 1
            
            # y2_lin
            item = QTableWidgetItem(f"{row_data['y2_lin']:.4e}")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.results_table.setItem(row_idx, col, item)
            col += 1
            
            # Δy2_lin%
            item = QTableWidgetItem(f"{row_data['y2_lin_percent']:.2f}%")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.results_table.setItem(row_idx, col, item)
            col += 1
            
            # y2_nlin
            item = QTableWidgetItem(f"{row_data['y2_nlin']:.4e}")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.results_table.setItem(row_idx, col, item)
            col += 1
            
            # Δy2_nlin%
            # item = QTableWidgetItem(f"{row_data['y2_nlin_percent']:.2f}%")
            # item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            # self.results_table.setItem(row_idx, col, item)
            # col += 1
    
    def _display_equations(self, a1_linear, a1_full, a2_linear, a2_full, mid_points, half_ranges):
        partLine = 65
        equations_text = []
        
        equations_text.append("=" * partLine + " ЛИНЕЙНЫЕ " + "=" * partLine)
        equations_text.append("Уравненения в нормированных координатах")
        equations_text.append("-" * partLine * 2)
        equations_text.append("y1 (среднее время ожидания типа 1):")
        eq_y1_norm = build_regression_equation_normalized_linear(a1_linear, FACTOR_NAMES)
        equations_text.append(eq_y1_norm)
        equations_text.append("")
        equations_text.append("y2 (среднее время ожидания типа 2):")
        eq_y2_norm = build_regression_equation_normalized_linear(a2_linear, FACTOR_NAMES)
        equations_text.append(eq_y2_norm)
        equations_text.append("-" * partLine * 2)
        equations_text.append("")
        
        equations_text.append("Уравненения в натуральных координатах")
        equations_text.append("-" * partLine * 2)
        equations_text.append("y1 (среднее время ожидания типа 1):")
        eq_y1_nat = build_regression_equation_natural_linear(a1_linear, FACTOR_NAMES, mid_points, half_ranges)
        equations_text.append(eq_y1_nat)
        equations_text.append("")
        equations_text.append("y2 (среднее время ожидания типа 2):")
        eq_y2_nat = build_regression_equation_natural_linear(a2_linear, FACTOR_NAMES, mid_points, half_ranges)
        equations_text.append(eq_y2_nat)
        equations_text.append("-" * partLine * 2)
        equations_text.append("")

        equations_text.append("=" * partLine + " НЕ ЛИНЕЙНЫЕ " + "=" * partLine)
        equations_text.append("Уравненения в нормированных координатах")
        equations_text.append("-" * partLine * 2)
        equations_text.append("y1 (среднее время ожидания типа 1):")
        eq_y1_norm = build_regression_equation_normalized_full(a1_full, FACTOR_NAMES)
        equations_text.append(eq_y1_norm)
        equations_text.append("")
        equations_text.append("y2 (среднее время ожидания типа 2):")
        eq_y2_norm = build_regression_equation_normalized_full(a2_full, FACTOR_NAMES)
        equations_text.append(eq_y2_norm)
        equations_text.append("-" * partLine * 2)
        equations_text.append("")
        
        equations_text.append("Уравненения в натуральных координатах")
        equations_text.append("-" * partLine * 2)
        equations_text.append("y1 (среднее время ожидания типа 1):")
        eq_y1_nat = build_regression_equation_natural_full(a1_full, FACTOR_NAMES, mid_points, half_ranges)
        equations_text.append(eq_y1_nat)
        equations_text.append("")
        equations_text.append("y2 (среднее время ожидания типа 2):")
        eq_y2_nat = build_regression_equation_natural_full(a2_full, FACTOR_NAMES, mid_points, half_ranges)
        equations_text.append(eq_y2_nat)
        equations_text.append("-" * partLine * 2)
        equations_text.append("")

        self.equations_text.setPlainText("\n".join(equations_text))
    
    def _on_calculate(self):
        try:
            mid_points = self._read_input_values()
            half_ranges = self._calculate_half_ranges()

            results = calculate_experiment_results(mid_points, half_ranges, self.design_matrix)
            
            self._populate_results_table(results['table_data'])
            self._display_equations(
                results['coefficients_y1_linear'],
                results['coefficients_y1_full'],
                results['coefficients_y2_linear'],
                results['coefficients_y2_full'],
                mid_points,
                half_ranges
            )
            
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка ввода", f"Некорректное числовое значение: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при расчете: {e}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()