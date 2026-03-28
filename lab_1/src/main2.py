import sys
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QLineEdit, 
                             QPushButton, QTextEdit, QMessageBox)
from smo import simulate_smo


class SMOGui(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Имитационная модель СМО (дисциплина обслуживания LIFO)")
        self.setGeometry(100, 100, 700, 500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        grid_layout = QGridLayout()

        label_law1 = QLabel("Закон распределения Рэлея:")
        font = label_law1.font()
        font.setBold(True)
        label_law1.setFont(font)
        grid_layout.addWidget(label_law1, 0, 0)
        grid_layout.addWidget(QLabel("lambda 1:"), 1, 0)
        self.lambda1_entry = QLineEdit("0.4")
        grid_layout.addWidget(self.lambda1_entry, 1, 1)

        grid_layout.addWidget(QLabel("lambda 2:"), 3, 0)
        self.lambda2_entry = QLineEdit("0.4")
        grid_layout.addWidget(self.lambda2_entry, 3, 1)

        label_law2 = QLabel("Равномерный закон распределения:")
        font = label_law2.font()
        font.setBold(True)
        label_law2.setFont(font)
        grid_layout.addWidget(label_law2, 4, 0)
        grid_layout.addWidget(QLabel("mu:"), 5, 0)
        self.mu_entry = QLineEdit("1.2")
        grid_layout.addWidget(self.mu_entry, 5, 1)

        # Блок для range
        grid_layout.addWidget(QLabel("range:"), 7, 0)
        self.rang_entry = QLineEdit("0.2")
        grid_layout.addWidget(self.rang_entry, 7, 1)

        cnt_entry = QLabel("Количество заявок:")
        font = cnt_entry.font()
        font.setBold(True)
        cnt_entry.setFont(font)
        grid_layout.addWidget(cnt_entry, 8, 0)
        self.num_entry = QLineEdit("1000")
        grid_layout.addWidget(self.num_entry, 8, 1)

        main_layout.addLayout(grid_layout)

        button_layout = QVBoxLayout()

        self.run_button = QPushButton("Запустить моделирование")
        self.run_button.clicked.connect(self.run_simulation)
        button_layout.addWidget(self.run_button)
        
        self.plot_wr_button = QPushButton("График зависимости среднего времени ожидания от загрузки")
        self.plot_wr_button.clicked.connect(self.plot_WR)
        button_layout.addWidget(self.plot_wr_button)
        
        self.plot_factors_button = QPushButton("Графики по факторам")
        self.plot_factors_button.clicked.connect(self.plot_factors)
        button_layout.addWidget(self.plot_factors_button)

        main_layout.addLayout(button_layout)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(200)
        main_layout.addWidget(self.result_text)

    def run_simulation(self):

        try:
            lambda1 = float(self.lambda1_entry.text())
            lambda2 = float(self.lambda2_entry.text())
            mu = float(self.mu_entry.text())
            rang = float(self.rang_entry.text())
            n = int(self.num_entry.text())

            R_calc, R_fact, avg_wait, avg_system, T = simulate_smo(
                lambda1, lambda2, mu, rang, n
            )
            if R_calc >= 1:
                QMessageBox.warning(self, "Внимание", "Система неустойчива (R ≥ 1)")

            self.result_text.clear()
            self.result_text.append(
                f"Время моделирования: {T:.3f}\n"
                f"Расчетная загрузка: {R_calc:.3f}\n"
                f"Фактическая загрузка: {R_fact:.3f}\n"
                f"Среднее время ожидания: {avg_wait:.3f}\n"
                f"Среднее время пребывания: {avg_system:.3f}\n"
            )

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def plot_WR(self):
        try:
            lambda1 = float(self.lambda1_entry.text())
            mu = float(self.mu_entry.text())
            rang = float(self.rang_entry.text())
            request = int(self.num_entry.text())
            Rs = []
            Wq = []

            lambda2 = 0.01
            runs = 30

            while lambda2 < mu - lambda1:
                wait_results = []
                for _ in range(runs):
                    R_calc, _, avg_wait, _, _ = simulate_smo(
                        lambda1, lambda2, mu, rang, request)
                    wait_results.append(avg_wait)

                Rs.append((lambda1 + lambda2) / mu)
                Wq.append(sum(wait_results) / len(wait_results))

                lambda2 += 0.05
                # print(f"{lambda2} < {mu - lambda1}")

            plt.figure()
            plt.plot(Rs, Wq, 'r')
            plt.xlabel("Загрузка")
            plt.ylabel("Среднее время ожидания")
            plt.title("Зависимость среднего времени ожидания от загрузки")
            plt.grid()
            plt.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def wait_lambda_1(self, lambda2, mu, rang, runs, request):
        l1_vals = []
        W1 = []

        x = 0.1
        while x < mu - lambda2:
            results = []
            for _ in range(runs):
                _, _, avg_wait, _, _ = simulate_smo(x, lambda2, mu, rang, request)
                results.append(avg_wait)

            l1_vals.append(x)
            W1.append(sum(results) / len(results))

            x += 0.1

        plt.figure()
        plt.plot(l1_vals, W1, 'r')
        plt.xlabel("lambda 1")
        plt.ylabel("Среднее время ожидания ")
        plt.title("Среднее время ожидания от lambda 1")
        plt.grid()
        plt.show()

    def wait_lambda_2(self, lambda1, mu, rang, runs, request):
        l2_vals = []
        W_lambda2 = []

        x = 0.1
        while x < mu - lambda1:
            results = []
            for _ in range(runs):
                _, _, avg_wait, _, _ = simulate_smo(lambda1, x, mu, rang, request)
                results.append(avg_wait)

            l2_vals.append(x)
            W_lambda2.append(sum(results) / len(results))

            x += 0.1

        plt.figure()
        plt.plot(l2_vals, W_lambda2, 'r')
        plt.xlabel("lambda 2")
        plt.ylabel("Среднее время ожидания")
        plt.title("Среднее время ожидания от lambda 2")
        plt.grid()
        plt.show()
    
    def wait_mu(self, lambda1, lambda2, rang, runs, request):
        mu_vals = []
        W_mu = []

        x = lambda1 + lambda2 + 0.2
        while x < 3:
            results = []
            for _ in range(runs):
                _, _, avg_wait, _, _ = simulate_smo(lambda1, lambda2, x, rang, request)
                results.append(avg_wait)

            mu_vals.append(x)
            W_mu.append(sum(results) / len(results))

            x += 0.2

        plt.figure()
        plt.plot(mu_vals, W_mu, 'r')
        plt.xlabel("mu")
        plt.ylabel("Среднее время ожидания")
        plt.title("Среднее время ожидания от mu")
        plt.grid()
        plt.show()

    def wait_rang(self, lambda1, lambda2, mu, runs, request):
        rang_vals = []
        W_rang = []

        x = 0.1
        while x < 10:
            results = []
            for _ in range(runs+20):
                _, _, avg_wait, _, _ = simulate_smo(lambda1, lambda2, mu, x, request)
                results.append(avg_wait)

            rang_vals.append(x)
            W_rang.append(sum(results) / len(results))

            x += 0.5

        window_size = 5
        except_end = 0
        smoothed_W_rang = W_rang.copy()  # Start with original values
        
        # Smooth all values except the last 5
        for i in range(len(W_rang) - except_end):
            start = max(0, i - window_size // 2)
            end = min(len(W_rang) - except_end, i + window_size // 2 + 1)
            smoothed_value = sum(W_rang[start:end]) / (end - start)
            smoothed_W_rang[i] = smoothed_value

        plt.figure()
        # plt.plot(rang_vals, W_rang, 'b-', alpha=0.5)
        plt.plot(rang_vals, smoothed_W_rang, 'r')
        plt.xlabel("rang")
        plt.ylabel("Среднее время ожидания")
        plt.title("Среднее время ожидания от rang")
        plt.grid()
        plt.show()

    def plot_factors(self):
        try:
            lambda1 = float(self.lambda1_entry.text())
            lambda2 = float(self.lambda2_entry.text())
            mu = float(self.mu_entry.text())
            rang = float(self.rang_entry.text())
            request = int(self.num_entry.text())
            runs = 30
            
            # self.wait_lambda_1(lambda2, mu, rang, runs, request)    # Wq(lambda 1)
            # self.wait_lambda_2(lambda1, mu, rang, runs, request)    # Wq(lambda 2)
            # self.wait_mu(lambda1, lambda2, rang, runs, request)     # Wq(mu)
            self.wait_rang(lambda1, lambda2, mu, runs, request)     # Wq(range)
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SMOGui()
    window.show()
    sys.exit(app.exec_())