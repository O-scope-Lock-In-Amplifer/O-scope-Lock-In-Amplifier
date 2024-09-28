# setup_panel.py
from typing import Type

from PySide2.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from oscilloscope import OScope, scope_types


class SetupPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout()

        # Dropdown for oscilloscope types
        self.scope_type_combo = QComboBox()
        self.scope_type_combo.addItems([scope.__name__ for scope in scope_types])
        self.scope_type_combo.currentIndexChanged.connect(self.populate_config)

        # Form layout for dynamic configuration
        self.form_layout = QFormLayout()
        self.config_widgets = {}

        # Scroll area for configuration
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.form_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)

        # Apply button
        self.apply_button = QPushButton("Apply Configuration")
        self.apply_button.clicked.connect(self.apply_configuration)

        self.layout.addWidget(QLabel("Select Oscilloscope Type:"))
        self.layout.addWidget(self.scope_type_combo)
        self.layout.addWidget(scroll)
        self.layout.addWidget(self.apply_button)

        self.setLayout(self.layout)

        # Initialize with first scope
        self.populate_config(0)

    def populate_config(self, index):
        # Clear existing widgets
        while self.form_layout.rowCount():
            self.form_layout.removeRow(0)
        self.config_widgets.clear()

        # Get selected scope class
        scope_class = scope_types[index]

        # Populate form with methods and their parameters
        # For simplicity, we'll assume methods have no parameters other than 'self'
        # Modify this as per actual method signatures
        for attr_name in dir(scope_class):
            attr = getattr(scope_class, attr_name)
            if callable(attr) and not attr_name.startswith("_"):
                # Example: For each method, create a checkbox or input as needed
                # Here, we'll create a checkbox to enable/disable methods
                checkbox = QCheckBox(attr_name)
                self.form_layout.addRow(QLabel(attr_name), checkbox)
                self.config_widgets[attr_name] = checkbox

    def apply_configuration(self):
        # Retrieve selected oscilloscope type
        scope_index = self.scope_type_combo.currentIndex()
        scope_class = scope_types[scope_index]

        # Instantiate the oscilloscope
        oscilloscope = scope_class()

        # Apply configurations based on user input
        for method_name, widget in self.config_widgets.items():
            if isinstance(widget, QCheckBox) and widget.isChecked():
                method = getattr(oscilloscope, method_name, None)
                if callable(method):
                    method()  # Call the method; modify as needed with parameters

        # Here, you can emit a signal or store the oscilloscope instance for use in the main application
        print(f"Configured oscilloscope: {oscilloscope}")
