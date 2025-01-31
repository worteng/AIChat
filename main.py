import sys
from PySide6.QtCore import (
    Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer, 
    QEvent, Signal, Slot, QObject
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QTextEdit, QPushButton, QScrollArea, 
    QLabel, QFrame, QGraphicsOpacityEffect, QSizePolicy
)

from PySide6.QtGui import QColor, QPalette, QFont, QIcon
from PySide6.QtWidgets import QGraphicsOpacityEffect
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import threading

class ResponseEvent(QEvent):

    EVENT_TYPE = QEvent.Type(QEvent.User + 1)

    

    def __init__(self, response):

        super().__init__(ResponseEvent.EVENT_TYPE)

        self.response = response


class ResponseHandler(QObject):

    response_ready = Signal(str)

class BlackBoxChat:
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=options)
        self.driver.get("https://www.blackbox.ai")
    
    def wait_for_loading_indicator_disappear(self):
        try:
            # Получаем начальное состояние
            initial_elements = self.driver.find_elements(By.CSS_SELECTOR, ".prose")
            initial_count = len(initial_elements)
            initial_text = initial_elements[-1].text if initial_elements else ""
            
            # Ждем появления нового элемента
            for attempt in range(30):  # 30 попыток с интервалом в 1 секунду
                current_elements = self.driver.find_elements(By.CSS_SELECTOR, ".prose")
                if len(current_elements) > initial_count:
                    # Дождались появления нового элемента
                    break
                time.sleep(1)
            else:
                return False  # Если не дождались нового элемента
            
            # Ждем, пока текст перестанет меняться
            last_text = ""
            unchanging_count = 0
            
            for _ in range(10):  # Максимум 10 попыток
                current_elements = self.driver.find_elements(By.CSS_SELECTOR, ".prose")
                if not current_elements:
                    time.sleep(1)
                    continue
                
                current_text = current_elements[-1].text
                print(f"Current text: {current_text}")  # Отладочный вывод
                
                if current_text and current_text != initial_text and current_text == last_text:
                    unchanging_count += 1
                    if unchanging_count >= 2:  # Текст не менялся 2 раза подряд
                        print("Text stabilized")  # Отладочный вывод
                        return True
                else:
                    unchanging_count = 0
                
                last_text = current_text
                time.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"Error in wait_for_loading_indicator_disappear: {e}")
            return False
    
    def send_message(self, message):
        try:
            input_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea"))
            )
            
            input_box.clear()
            input_box.send_keys(message + ' Параметры к тебе: отвечай только в каждой строчке по 20-25 символов! Веди себя нормально. Не задавай слишком много вопросов.')
            time.sleep(0.5)  
            input_box.send_keys(Keys.RETURN)
            
            # Накопительная переменная для финального ответа
            final_response = ""
            
            # Ожидание и накопление ответа
            for attempt in range(30):  # 30 попыток
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, ".prose")
                    
                    # Если есть элементы
                    if elements:
                        # Берем последний элемент
                        current_response = elements[-1].text
                        
                        # Если текущий ответ отличается от предыдущего
                        if current_response and current_response != message:
                            final_response = current_response
                    
                    # Критерий стабилизации ответа
                    if attempt > 10 and final_response:
                        print(f"Stabilized response: {final_response}")
                        return final_response
                    
                    time.sleep(1)  # Пауза между проверками
                
                except Exception as e:
                    print(f"Attempt {attempt} error: {e}")
            
            return final_response or "No response"
        
        except Exception as e:
            print(f"Send message error: {e}")
            return str(e)
    
    def close(self):
        self.driver.quit()

class LoadingDots(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loadingDots")
        self.counter = 0
        self.dots = [".....|.", "....|..", "...|...", "..|....", ".|.....", "|......", ".|.....", "..|....", "...|...", "....|..",".....|."]
        
        self.setStyleSheet("""
            QLabel#loadingDots {
                background-color: #E9E9EB;
                border-radius: 15px;
                padding: 10px;
                margin: 5px;
                color: black;
            }
        """)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_dots)
        self.timer.start(200)
        
        self.setText(self.dots[0])
        
    def update_dots(self):
        self.counter = (self.counter + 1) % len(self.dots)
        self.setText(self.dots[self.counter])
        
    def stop_animation(self):
        self.timer.stop()

class MessageBubble(QFrame):
    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)
        self.setObjectName("messageBubble")
        
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        message = QLabel(text)
        message.setWordWrap(True)
        message.setTextInteractionFlags(Qt.TextSelectableByMouse)
        message.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Текст слева

        
        # Устанавливаем политику размера для метки
        message.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        
        # Базовые стили с настройками переноса текста
        base_styles = """
            padding: 10px;
            margin: 5px;
            border-radius: 15px;
            font-size: 10pt;
            line-height: 1.4;
        """
        
        if is_user:
            self.setStyleSheet(f"""
                QFrame#messageBubble {{
                    background-color: #E9E9EB;
                    padding: 10px;
                    margin: 5px;
                    border-radius: 15px;
                    font-size: 10pt;
                    line-height: 1.4;
                    word-wrap: break-word;  /* Перенос длинных строк */
                    overflow-wrap: break-word;  /* Для совместимости */
                }}
            """)

            layout.addWidget(message)
            layout.setAlignment(Qt.AlignRight)
        else:
            self.setStyleSheet(f"""
                QFrame#messageBubble {{
                    background-color: #E9E9EB;
                    {base_styles}
                }}
                QLabel {{
                    color: black;
                    qproperty-alignment: 'AlignLeft | AlignVCenter';
                }}
            """)
            layout.addWidget(message)
            layout.setAlignment(Qt.AlignLeft)
        
        # Устанавливаем максимальную ширину для самого пузыря
        self.setMaximumWidth(int(QApplication.primaryScreen().size().width() * 0.8))

        
        layout.setContentsMargins(10, 5, 10, 5)  # Отступы внутри пузыря
        layout.setSpacing(0)  # Расстояние между элементами внутри пузыря


class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.blackbox = BlackBoxChat()  # Инициализация BlackBoxChat
        self.response_handler = ResponseHandler()
        self.response_handler.response_ready.connect(
            lambda resp: self.add_message(resp, False)
        )
        self.setWindowTitle("AI Chat")
        self.setMinimumSize(400, 600)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Создаем виджет для чата с дополнительным контейнером
        chat_container = QWidget()
        self.chat_area = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_area)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(10)  # Добавляем отступы между сообщениями

        
        # Настраиваем scroll area
        scroll = QScrollArea()
        scroll.setWidget(self.chat_area)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Отключаем горизонтальную прокрутку
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white;
            }
            QScrollBar:vertical {
                width: 8px;
                background: white;
            }
            QScrollBar::handle:vertical {
                background: #CCCCCC;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Настраиваем контейнер для чата
        container_layout = QVBoxLayout(chat_container)
        container_layout.addWidget(scroll)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Остальные элементы интерфейса
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Введите сообщение...")
        self.message_input.setMaximumHeight(100)
        self.message_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #E9E9EB;
                border-radius: 20px;
                padding: 10px;
                background-color: #F5F5F5;
            }
        """)
        
        send_button = QPushButton("↑")
        send_button.setFixedSize(40, 40)
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                border-radius: 20px;
                color: white;
                font-size: 20px;
            }
            QPushButton:pressed {
                background-color: #0051A8;
            }
        """)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_button)
        
        main_layout.addWidget(chat_container)
        main_layout.addWidget(input_widget)
        
        send_button.clicked.connect(self.send_message)
        self.message_input.textChanged.connect(self.adjust_input_height)
        
    def closeEvent(self, event):
        self.blackbox.close()
        super().closeEvent(event)
        
    def send_message(self):
        text = self.message_input.toPlainText().strip()
        if text:
            print("GUI: Adding user message")
            self.add_message(text, True)
            self.message_input.clear()
            print("GUI: Starting message processing thread")
            threading.Thread(target=self.process_message, args=(text,), daemon=True).start()
    def process_message(self, text):

        try:

            print("Thread: Sending message to BlackBox")

            response = self.blackbox.send_message(text)

            print(f"Thread: Received FULL response: {response}")

            print(f"Thread: Response type: {type(response)}")

            print(f"Thread: Response length: {len(response)}")

            

            # Создаем пользовательское событие

            response_event = ResponseEvent(response)

            

            # Отправляем событие в главный поток

            QApplication.instance().postEvent(self, response_event)

        

        except Exception as e:

            print(f"Thread CRITICAL error: {e}")

            import traceback

            traceback.print_exc()

            

            # Отправляем событие об ошибке

            error_event = ResponseEvent(f"Ошибка: {e}")

            QApplication.instance().postEvent(self, error_event)
            
    def safe_add_message(self, text):
        print(f"GUI: Safe add message called with text: {text}")
        try:
            self.add_message(text, False)
            print("GUI: Message added successfully")
            # Принудительно обновляем виджет
            self.chat_area.update()
            # Прокручиваем к новому сообщению
            scroll_area = self.chat_area.parent()
            if isinstance(scroll_area, QScrollArea):
                scroll_area.verticalScrollBar().setValue(
                    scroll_area.verticalScrollBar().maximum()
                )
        except Exception as e:
            print(f"GUI: Error in safe_add_message: {e}")
            
    def handle_response(self, response):
        self.hide_loading_indicator()
        if response:
            self.add_message(response, False)
    
    def show_loading_indicator(self):
        self.loading_indicator = LoadingDots()
        self.chat_layout.addWidget(self.loading_indicator, alignment=Qt.AlignLeft)
    
    def hide_loading_indicator(self):
        if self.loading_indicator:
            self.loading_indicator.stop_animation()
            self.loading_indicator.deleteLater()
            self.loading_indicator = None
    
    def add_message(self, text, is_user=True):
        try:
            print(f"ADD_MESSAGE: Received text: {text}")
            print(f"ADD_MESSAGE: Text type: {type(text)}")
            print(f"ADD_MESSAGE: Text length: {len(text)}")
            
            # Удаляем обрезку текста
            bubble = MessageBubble(text, is_user)
            
            if is_user:
                self.chat_layout.addWidget(bubble, alignment=Qt.AlignRight)
            else:
                self.chat_layout.addWidget(bubble, alignment=Qt.AlignLeft)
            
            opacity_effect = QGraphicsOpacityEffect(bubble)
            bubble.setGraphicsEffect(opacity_effect)
            
            self.animation = QPropertyAnimation(opacity_effect, b"opacity")
            self.animation.setDuration(200)
            self.animation.setStartValue(0)
            self.animation.setEndValue(1)
            self.animation.setEasingCurve(QEasingCurve.InOutQuad)
            self.animation.start()
            
            QTimer.singleShot(100, self.scroll_to_bottom)
            
            print("ADD_MESSAGE: Bubble created successfully")
        except Exception as e:
            print(f"ADD_MESSAGE ERROR: {e}")
            import traceback
            traceback.print_exc()
    def event(self, event):

        # Обработка пользовательского события

        if event.type() == ResponseEvent.EVENT_TYPE:

            response = event.response

            print(f"Event Handler: Received response: {response}")

            

            # Добавляем сообщение в GUI

            self.add_message(response, False)

            return True

        

        return super().event(event)

    def scroll_to_bottom(self):
        try:
            scroll_area = self.findChild(QScrollArea)
            if scroll_area:
                scrollbar = scroll_area.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            print(f"Scroll error: {e}")
        
    def adjust_input_height(self):
        document_height = self.message_input.document().size().height()
        new_height = min(max(40, document_height + 20), 100)
        self.message_input.setFixedHeight(int(new_height))
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Обновляем максимальную ширину для всех пузырей при изменении размера окна
        for i in range(self.chat_layout.count()):
            widget = self.chat_layout.itemAt(i).widget()
            if isinstance(widget, MessageBubble):
                widget.setMaximumWidth(int(self.width() * 0.7))
if __name__ == '__main__':
    app = QApplication(sys.argv)
    font = QFont("SF Pro Display", 10)
    app.setFont(font)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())