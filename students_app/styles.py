MAIN_STYLE = """
/* Общий стиль для всех виджетов */
QWidget {
    background-color: #FFFFFF; /* Белый фон */
    color: #333333; /* Темно-серый текст для лучшей читаемости */
    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    font-size: 14px;
}

/* Стиль для кнопок */
QPushButton {
    background-color: #F0F0F0;   /* Светло-серый фон кнопок */
    border: 2px solid #CCCCCC;   /* Серый бордер */
    border-radius: 10px;         /* Закругленные углы */
    padding: 10px;
    min-width: 250px;            /* Минимальная ширина */
}

QPushButton:hover {
    background-color: #E0E0E0; /* Темно-серый при наведении */
    border-color: #999999; /* Темнее бордер при наведении */
}

QPushButton:pressed {
    background-color: #D0D0D0; /* Еще темнее при нажатии */
    border-color: #777777;
}

/* Стиль для заголовков */
QLabel {
    font-size: 18px;
    font-weight: bold;
    color: #333333;
}

/* Стиль для таблиц */
QTableWidget {
    background-color: #FFFFFF; /* Белый фон таблиц */
    border: 1px solid #CCCCCC;
    gridline-color: #DDDDDD;
}

QTableWidget::item:selected {
    background-color: #FFE5B4;
    color: #000000;
    border: 1px solid #FFA500;  
}

QHeaderView::section {
    background-color: #F5F5F5; /* Светло-серый фон заголовков */
    padding: 5px;
    border: 1px solid #CCCCCC;
    font-size: 16px;
}

/* Стиль для полей ввода */
QLineEdit, QTextEdit, QComboBox {
    border: 1px solid #CCCCCC;
    border-radius: 5px;
    padding: 5px;
    background-color: #FFFFFF;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 2px solid #6666FF; /* Синий бордер при фокусе */
}
"""
