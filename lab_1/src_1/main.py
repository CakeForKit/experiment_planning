# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5 import uic
import sys
import usystem
import laws 

UI_MAINWINDOW_PATH = "./mod7_6/ui/mainWindow.ui"

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = uic.loadUi(UI_MAINWINDOW_PATH, self)
        
        self.system = None  
        self.connect_buttons()
        self.update_system_parameters()

    def connect_buttons(self):
        self.ui.modeling_btn.clicked.connect(self.modeling)

    def modeling(self):
        try:
            self.update_system_parameters()
            self.system.simulate()
            self.display_results()
            
        except Exception as e:
            self.show_error(f"Ошибка при моделировании: {str(e)}")

    def update_system_parameters(self):
        try:
            client_avg = self.ui.client_spb.value() 
            client_delta = self.ui.client_delta_spb.value() 
            
            op1_avg = self.ui.op1_spb.value()
            op1_delta = self.ui.op1_delta_spb.value()
            
            op2_avg = self.ui.op2_spb.value()
            op2_delta = self.ui.op2_delta_spb.value()
            
            op3_avg = self.ui.op3_spb.value()
            op3_delta = self.ui.op3_delta_spb.value()

            op4_avg = self.ui.op4_spb.value()
            op4_delta = self.ui.op4_delta_spb.value()
            
            comp1_const = self.ui.comp1_spb.value()
            comp2_const = self.ui.comp2_spb.value()
            comp3_const = self.ui.comp3_spb.value()
            
            n = self.ui.n_spb.value()

            clientLaw = laws.UniformDistributionLaw(a=client_avg-client_delta, b=client_avg+client_delta)
            operators = [
                usystem.Operator(laws.UniformDistributionLaw(a=op1_avg-op1_delta, b=op1_avg+op1_delta), usystem.OP1_EVENT),
                usystem.Operator(laws.UniformDistributionLaw(a=op2_avg-op2_delta, b=op2_avg+op2_delta), usystem.OP2_EVENT),
                usystem.Operator(laws.UniformDistributionLaw(a=op3_avg-op3_delta, b=op3_avg+op3_delta), usystem.OP3_EVENT),
                usystem.Operator(laws.UniformDistributionLaw(a=op4_avg-op4_delta, b=op4_avg+op4_delta), usystem.OP4_EVENT),
            ]
            computer1 = usystem.Computer(laws.ConstantDistributionLaw(comp1_const), usystem.COMP1_EVENT)
            computer2 = usystem.Computer(laws.ConstantDistributionLaw(comp2_const), usystem.COMP2_EVENT)
            computer3 = usystem.Computer(laws.ConstantDistributionLaw(comp3_const), usystem.COMP3_EVENT)
            N = n
            self.system = usystem.System(clientLaw, operators, computer1, computer2, computer3, N)
            
        except ValueError as e:
            raise ValueError(f"Некорректные значения параметров: {str(e)}")
        except Exception as e:
            raise Exception(f"Ошибка обновления параметров: {str(e)}")

    def display_results(self):
        try:
            generated_count = self.system.generated_count
            processed_count = self.system.processed_count
            rejected_count = self.system.rejected_count
            avg_waiting_queue_1 = self.system.avg_time_waiting_queue1()
            avg_waiting_queue_2 = self.system.avg_time_waiting_queue2()
            self.ui.processed_count_line_edit.setText(str(processed_count))
            self.ui.rejected_count_line_edit.setText(str(rejected_count))
            self.ui.avg_waiting_queue_1_line_edit.setText(f"{avg_waiting_queue_1:.2f}")
            self.ui.avg_waiting_queue_2_line_edit.setText(f"{avg_waiting_queue_2:.2f}")
            # print("generated_count = ", generated_count)

            total_requests = processed_count + rejected_count
            if total_requests > 0:
                rejection_probability = rejected_count / total_requests
                self.ui.rejected_probability_line_edit.setText(f"{rejection_probability:.4f}")
            else:
                self.ui.rejected_probability_line_edit.setText("0.0000")
                
        except Exception as e:
            self.show_error(f"Ошибка отображения результатов: {str(e)}")

    def show_error(self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Ошибка")
        msg.setInformativeText(message)
        msg.setWindowTitle("Ошибка")
        msg.exec_()

    def closeEvent(self, event):
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
