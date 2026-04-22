import sys
import re
from itertools import combinations, product
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QTabWidget, QLabel, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                             QTextEdit, QScrollArea, QGroupBox, QFrame, QHeaderView,
                             QMessageBox)
from PyQt5.QtCore import Qt
from smo import simulate_smo
from full_factorial import FullFactorialWidget
from consts import *


x_to_sym = {
    "x1": "λ1",
    "x2": "λ2", 
    "x3": "μ",
    "x4": "r"
}
sym_to_x = {
    "λ1": "x1",
    "λ2": "x2",
    "μ": "x3",
    "r": "x4"
}

factor_symbols = list(FACTOR_RANGES.keys())


# --- Вспомогательные функции ---

def build_regression_equation_norm(b, factor_symbols):
    n = len(factor_symbols)
    terms = ["1"] + factor_symbols.copy()
    
    for comb in combinations(range(n), 2):
        terms.append("".join([factor_symbols[i] for i in comb]))
    eq = "y = " + " + ".join(f"{b[i]:.4f}*{terms[i]}" for i in range(len(terms)))
    return eq

def build_regression_equation_norm_dfe(b, factor_symbols):
    terms = ["1"] + factor_symbols
    
    eq = "y = " + " + ".join(
        f"{b[i]:.4f}*{terms[i]}" for i in range(len(b))
    )
    return eq

def build_regression_nat_dfe(b, factor_symbols, X_mid, X_delta):
    n = len(factor_symbols)
    
    eq_terms = []
    
    # свободный член
    c0 = b[0] + sum(b[i+1]*X_mid[i] for i in range(n))
    eq_terms.append(f"{c0:.4f}")
    
    # линейные (ВСЕ 6 факторов)
    for i in range(n):
        coef = b[i+1] * X_delta[i]
        eq_terms.append(f"{coef:.4f}*{factor_symbols[i]}")
    
    return " + ".join(eq_terms)

def build_full_nonlinear_equation(b, factor_symbols):
    n = len(factor_symbols)
    
    terms = ["1"]
    
    for r in range(1, n + 1):
        for comb in combinations(range(n), r):
            terms.append("".join(factor_symbols[i] for i in comb))
    
    return " + ".join(
        f"{b[i]:.4f}*{terms[i]}" for i in range(len(b))
    )

def build_full_nonlinear_nat(b, factor_symbols, X_mid, X_delta):
    n = len(factor_symbols)
    terms = []
    idx = 0
    for r in range(0, n + 1):
        for comb in combinations(range(n), r):
            coef = b[idx]
            for i in comb:
                coef *= X_delta[i]
            if len(comb) == 0:
                term = "1"
            else:
                term = "*".join(factor_symbols[i] for i in comb)
            terms.append(f"{coef:.4f}*{term}")
            idx += 1
    
    return " + ".join(terms)

def build_defining_relation(relations):
    if not relations:
        return "I = 1"
    
    def normalize(term):
        counts = {}
        for t in term:
            counts[t] = counts.get(t, 0) + 1
        
        result = []
        for k, v in counts.items():
            if v % 2 == 1:
                result.append(k)
        
        return sorted(result)
    
    generators = []
    
    for left, right in relations.items():
        left_x = sym_to_x.get(left, left)
        right_x = [sym_to_x.get(r, r) for r in right]
        
        expr = right_x + [left_x]
        generators.append(expr)
    
    closure = set()
    
    def to_str(lst):
        return "".join(lst) if lst else "1"
    
    for g in generators:
        closure.add(to_str(g))
    
    for i in range(len(generators)):
        for j in range(i + 1, len(generators)):
            prod = generators[i] + generators[j]
            prod = normalize(prod)
            closure.add(to_str(prod))
    
    return "I = " + " = ".join(sorted(closure))

def get_defining_group(relations):
    def normalize(prod):
        counts = {}
        for t in prod:
            counts[t] = counts.get(t, 0) + 1
        return tuple(sorted([k for k, v in counts.items() if v % 2 == 1]))
    
    generators = []
    for left, right in relations.items():
        left_x = sym_to_x[left]
        right_x = [sym_to_x[r] for r in right]
        generators.append(right_x + [left_x])
    
    group = {tuple()}
    
    changed = True
    while changed:
        new_group = set(group)
        for g in generators:
            for h in group:
                new_group.add(normalize(list(g) + list(h)))
        changed = len(new_group) != len(group)
        group = new_group
    
    return group

def build_alias_lines(generators, factors, dependent_factors, relations):
    def normalize(prod):
        counts = {}
        for t in prod:
            counts[t] = counts.get(t, 0) + 1
        return tuple(sorted([k for k, v in counts.items() if v % 2 == 1]))
    
    def fmt(x):
        return "".join(x) if x else "I"
    
    group = list(get_defining_group(relations))
    
    lines = []
    
    base_factors = [sym_to_x[s] for s in factor_symbols if s not in dependent_factors]
    
    for f in base_factors:
        base = (f,)
        aliases = set()
        
        for g in group:
            aliases.add(normalize(list(base) + list(g)))
        
        sorted_alias = sorted(aliases, key=lambda x: (len(x), "".join(x)))
        
        line = f"{f}: " + " = ".join(fmt(x) for x in sorted_alias)
        lines.append(line)
    
    return "\n".join(lines)

def create_dfe_matrix(factor_symbols, relations, dependent_factors):
    independent = [s for s in factor_symbols if s not in dependent_factors]
    
    matrix = []
    
    for row in product([-1, 1], repeat=len(independent)):
        row_dict = dict(zip(independent, row))
        
        unresolved = set(relations.keys())
        
        while unresolved:
            progress = False
            
            for dep in list(unresolved):
                factors = relations[dep]
                
                if all(f in row_dict for f in factors):
                    val = 1
                    for f in factors:
                        val *= row_dict[f]
                    
                    row_dict[dep] = val
                    unresolved.remove(dep)
                    progress = True
            
            if not progress:
                raise ValueError(
                    f"Невозможно вычислить зависимости. Проверь соотношения: {relations}"
                )
        
        full_row = [row_dict[sym] for sym in factor_symbols]
        matrix.append(full_row)
    
    return matrix

def expand_nonlinear(row):
    feats = [1]
    
    n = len(row)
    
    for r in range(1, n + 1):
        for comb in combinations(range(n), r):
            val = 1
            for i in comb:
                val *= row[i]
            feats.append(val)
    
    return feats

class FractionalFactorialWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.relation_entries = []
        self.range_entries = {}
        self.relations = {}
        self.dependent_factors = set()
        self.ui_init()
        
    def ui_init(self):
        layout = QVBoxLayout()
        
        # Скролл-область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Количество прогонов
        runs_layout = QHBoxLayout()
        runs_layout.addWidget(QLabel("Количество генерирующих соотношений:"))
        self.runs_entry = QLineEdit()
        self.runs_entry.setText("1")
        runs_layout.addWidget(self.runs_entry)
        
        btn_set = QPushButton("Задать")
        btn_set.clicked.connect(self.ui_update_relations)
        runs_layout.addWidget(btn_set)
        scroll_layout.addLayout(runs_layout)
        
        # Соотношения
        self.relations_frame = QWidget()
        self.relations_layout = QVBoxLayout(self.relations_frame)
        scroll_layout.addWidget(self.relations_frame)
        
        # Диапазоны
        self.range_frame = QWidget()
        self.range_layout = QGridLayout(self.range_frame)
        scroll_layout.addWidget(self.range_frame)
        
        btn_update = QPushButton("Обновить факторы")
        btn_update.clicked.connect(self.update_all)
        scroll_layout.addWidget(btn_update)
        
        # Таблица
        columns = ["№"] + factor_symbols + ["y1","y1_lin","y1_nlin","Δy1_lin","Δy1_nlin",
                                           "y2","y2_lin","y2_nlin","Δy2_lin","Δy2_nlin"]
        
        self.table = QTableWidget()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.horizontalHeader().setStretchLastSection(True)
        scroll_layout.addWidget(self.table)
        
        # Уравнения
        eq_group = QGroupBox("Регрессионные уравнения")
        eq_layout = QVBoxLayout()
        self.text_eq = QTextEdit()
        self.text_eq.setReadOnly(True)
        eq_layout.addWidget(self.text_eq)
        eq_group.setLayout(eq_layout)
        scroll_layout.addWidget(eq_group)
        
        # Результат ДФЭ
        def_group = QGroupBox("Результат ДФЭ")
        def_layout = QVBoxLayout()
        self.text_def = QTextEdit()
        self.text_def.setReadOnly(True)
        def_layout.addWidget(self.text_def)
        def_group.setLayout(def_layout)
        scroll_layout.addWidget(def_group)
        
        # Кнопка расчета
        btn_calc = QPushButton("Вычислить ДФЭ")
        btn_calc.clicked.connect(self.calculate)
        scroll_layout.addWidget(btn_calc)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        self.setLayout(layout)
        
        self.ui_update_relations()
        self.ui_rebuild_ranges()
    
    def ui_parse_relations(self):
        self.relations = {}
        self.dependent_factors = set()
        
        for entry in self.relation_entries:
            text = entry.text().strip()
            
            if "=" not in text:
                continue
            
            left, right = text.split("=")
            left = left.strip()
            
            right_factors = re.findall(r"x\d+", right)
            
            left_sym = x_to_sym.get(left)
            right_syms = [x_to_sym.get(f) for f in right_factors]
            
            if left_sym:
                self.relations[left_sym] = right_syms
                self.dependent_factors.add(left_sym)
    
    def ui_update_relations(self):
        # Очищаем старые виджеты И layouts
        for i in reversed(range(self.relations_layout.count())):
            item = self.relations_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.ui_clear_layout(item.layout())
                self.relations_layout.removeItem(item)
        self.relation_entries.clear()
        
        try:
            count = int(self.runs_entry.text())
        except:
            return
        
        label = QLabel("Генерирующие соотношения:")
        self.relations_layout.addWidget(label)
        
        for i in range(count):
            h_layout = QHBoxLayout()
            h_layout.addWidget(QLabel(f"Соотношение {i+1}:"))
            entry = QLineEdit()
            entry.setMaximumWidth(250)
            h_layout.addWidget(entry)
            self.relations_layout.addLayout(h_layout)
            self.relation_entries.append(entry)
    
    def ui_clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                self.ui_clear_layout(item.layout())

    def ui_rebuild_ranges(self):
        # Очищаем старые виджеты
        for i in reversed(range(self.range_layout.count())):
            widget = self.range_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        self.range_entries.clear()
        
        label = QLabel("Диапазон факторов")
        self.range_layout.addWidget(label, 0, 0, 1, 10)
        
        self.range_layout.addWidget(QLabel("min"), 2, 0)
        self.range_layout.addWidget(QLabel("max"), 3, 0)
        
        active_factors = [s for s in factor_symbols if s not in self.dependent_factors]
        
        for i, sym in enumerate(active_factors):
            self.range_layout.addWidget(QLabel(f"{sym_to_x[sym]} ({sym})"), 1, i+1)
            
            e_min = QLineEdit()
            e_min.setText(str(FACTOR_RANGES[sym][0]))
            e_min.setMaximumWidth(80)
            self.range_layout.addWidget(e_min, 2, i+1)
            
            e_max = QLineEdit()
            e_max.setText(str(FACTOR_RANGES[sym][1]))
            e_max.setMaximumWidth(80)
            self.range_layout.addWidget(e_max, 3, i+1)
            
            self.range_entries[sym] = (e_min, e_max)
    
    def update_all(self):
        self.ui_parse_relations()
        self.ui_rebuild_ranges()
    
    def calculate(self):
        try:
            self.ui_parse_relations()
            defining_relation = build_defining_relation(self.relations)
            m = len(self.dependent_factors)
            replication_order = 2 ** m
            num_replaced_factors = len(self.dependent_factors)
            
            generating_relations = []
            for e in self.relation_entries:
                t = e.text().strip()
                if t:
                    generating_relations.append(t)
            
            generating_relations_text = ", ".join(generating_relations) if generating_relations else "—"
            
            generators = []
            for left, right in self.relations.items():
                left_x = sym_to_x.get(left, left)
                right_x = [sym_to_x.get(r, r) for r in right]
                generators.append(right_x + [left_x])
            
            base_factors = [s for s in factor_symbols if s not in self.dependent_factors]
            alias_text = build_alias_lines(generators, base_factors, self.dependent_factors, self.relations)
            
            final_text = (
                f"кратность реплики: {replication_order}\n"
                f"количество заменённых факторов: {num_replaced_factors}\n"
                f"генерирующие соотношения: {generating_relations_text}\n"
                f"определяющий контраст: {defining_relation}\n"
                f"схема смешивания:\n{alias_text}"
            )
            
            self.text_def.clear()
            self.text_def.setText(final_text)
            
            X_min, X_max = {}, {}
            
            for sym, (e_min, e_max) in self.range_entries.items():
                X_min[sym] = float(e_min.text())
                X_max[sym] = float(e_max.text())
            
            matrix = create_dfe_matrix(factor_symbols, self.relations, self.dependent_factors)
            matrix_nl = [expand_nonlinear(row) for row in matrix]
            
            real_values = []
            for row in matrix:
                vals = []
                for i, sym in enumerate(factor_symbols):
                    if sym in self.range_entries:
                        mid = (X_max[sym] + X_min[sym]) / 2
                        delta = (X_max[sym] - X_min[sym]) / 2
                    else:
                        min_val, max_val = FACTOR_RANGES[sym]
                        mid = (min_val + max_val) / 2
                        delta = (max_val - min_val) / 2
                    
                    vals.append(mid + row[i] * delta)
                
                real_values.append(vals)
            
            y1_list, y2_list = [], []
            max_requests = 1000
            
            for values in real_values:
                lam1, lam2, mu, r = values  # ИЗМЕНЕНО: распаковка для 4 факторов
                _, _, y1, y2, _, _ = simulate_smo(lam1, lam2, mu, r, max_requests)
                
                y1_list.append(y1)
                y2_list.append(y2)
            
            N = len(matrix)
            matrix1 = [[1] + row for row in matrix]
            
            b1 = [sum(matrix1[i][j]*y1_list[i] for i in range(N))/N for j in range(len(matrix1[0]))]
            b2 = [sum(matrix1[i][j]*y2_list[i] for i in range(N))/N for j in range(len(matrix1[0]))]
            
            b1_nl = [
                sum(matrix_nl[i][j] * y1_list[i] for i in range(len(matrix_nl))) / len(matrix_nl)
                for j in range(len(matrix_nl[0]))
            ]
            
            b2_nl = [
                sum(matrix_nl[i][j] * y2_list[i] for i in range(len(matrix_nl))) / len(matrix_nl)
                for j in range(len(matrix_nl[0]))
            ]
            
            # Заполнение таблицы
            self.table.setRowCount(len(matrix))
            
            for i, row in enumerate(matrix):
                row1 = [1] + row
                num_factors = len(b1) - 1
                y1_lin = b1[0] + sum(b1[k+1]*row[k] for k in range(num_factors))
                y1_nlin = sum(b1[j]*row1[j] for j in range(len(b1)))
                delta1_lin = abs(y1_list[i]-y1_lin)
                delta1_nlin = abs(y1_list[i]-y1_nlin)
                
                y2_lin = b2[0] + sum(b2[k+1]*row[k] for k in range(num_factors))
                y2_nlin = sum(b2[j]*row1[j] for j in range(len(b2)))
                delta2_lin = abs(y2_list[i]-y2_lin)
                delta2_nlin = abs(y2_list[i]-y2_nlin)
                
                self.table.setItem(i, 0, QTableWidgetItem(str(i+1)))
                for j, val in enumerate(row):
                    self.table.setItem(i, j+1, QTableWidgetItem(f"{val:.0f}"))
                
                values = [
                    f"{y1_list[i]:.2e}", f"{y1_lin:.2e}", f"{y1_nlin:.2e}",
                    f"{delta1_lin:.2e}", f"{delta1_nlin:.2e}",
                    f"{y2_list[i]:.2e}", f"{y2_lin:.2e}", f"{y2_nlin:.2e}",
                    f"{delta2_lin:.2e}", f"{delta2_nlin:.2e}"
                ]
                
                for j, val in enumerate(values):
                    self.table.setItem(i, j+NUM_FACTORS+1, QTableWidgetItem(val))
            
            # Уравнения
            eq_y1_norm = build_regression_equation_norm_dfe(b1, factor_symbols)
            eq_y2_norm = build_regression_equation_norm_dfe(b2, factor_symbols)
            
            eq_y1_nl = build_full_nonlinear_equation(b1_nl, factor_symbols)
            eq_y2_nl = build_full_nonlinear_equation(b2_nl, factor_symbols)
            
            X_mid = [(FACTOR_RANGES[s][0] + FACTOR_RANGES[s][1]) / 2 for s in factor_symbols]
            X_delta = [(FACTOR_RANGES[s][1] - FACTOR_RANGES[s][0]) / 2 for s in factor_symbols]
            
            eq_y1_nat = build_regression_nat_dfe(b1, factor_symbols, X_mid, X_delta)
            eq_y2_nat = build_regression_nat_dfe(b2, factor_symbols, X_mid, X_delta)
            
            eq_y1_nat_nl = build_full_nonlinear_nat(b1_nl, factor_symbols, X_mid, X_delta)
            eq_y2_nat_nl = build_full_nonlinear_nat(b2_nl, factor_symbols, X_mid, X_delta)
            
            self.text_eq.clear()
            self.text_eq.append("==============================")
            self.text_eq.append("ЛИНЕЙНАЯ МОДЕЛЬ (НОРМИРОВАННАЯ)")
            self.text_eq.append("==============================")
            self.text_eq.append(f"y1: {eq_y1_norm}")
            self.text_eq.append(f"y2: {eq_y2_norm}\n")
            
            self.text_eq.append("==============================")
            self.text_eq.append("ЛИНЕЙНАЯ МОДЕЛЬ (НАТУРАЛЬНАЯ)")
            self.text_eq.append("==============================")
            self.text_eq.append(f"y1 = {eq_y1_nat}")
            self.text_eq.append(f"y2 = {eq_y2_nat}\n")
            
            self.text_eq.append("==============================")
            self.text_eq.append("НЕЛИНЕЙНАЯ МОДЕЛЬ (НОРМИРОВАННАЯ)")
            self.text_eq.append("==============================")
            self.text_eq.append(f"y1 = {eq_y1_nl}\n")
            self.text_eq.append(f"y2 = {eq_y2_nl}\n")
            
            self.text_eq.append("==============================")
            self.text_eq.append("НЕЛИНЕЙНАЯ МОДЕЛЬ (НАТУРАЛЬНАЯ)")
            self.text_eq.append("==============================")
            self.text_eq.append(f"y1 = {eq_y1_nat_nl}\n")
            self.text_eq.append(f"y2 = {eq_y2_nat_nl}\n")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка ДФЭ", str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Имитационная модель СМО (дисциплина обслуживания LIFO)")
        self.setGeometry(0, 0, 1200, 800)
        
        tabs = QTabWidget()
        tabs.addTab(FractionalFactorialWidget(), "ДФЭ")
        tabs.addTab(FullFactorialWidget(), "ПФЭ")
        self.setCentralWidget(tabs)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()