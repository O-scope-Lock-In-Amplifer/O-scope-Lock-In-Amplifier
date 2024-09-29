# setup_panel.py

from enum import Enum
import inspect
import logging
from typing import Any, Dict, List, Optional, Type

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from o_scope_lock_in_amplifier import scope_types
from o_scope_lock_in_amplifier.oscilloscope_utils import OScope

logger = logging.getLogger("o_scope_lock_in_amplifier")


# Base class for type handlers
class TypeHandler:
    def create_widget(
        self,
        annotation: Any,
        allowed_values: Optional[List[Any]] = None,
        default: Any = None,
    ) -> QWidget:
        """Create and return a widget based on the type annotation."""
        raise NotImplementedError

    def get_value(self, widget: QWidget, annotation: Any) -> Optional[Any]:
        """Retrieve and convert the value from the widget based on the type annotation."""
        raise NotImplementedError


# Handler for integer types
class IntHandler(TypeHandler):
    def create_widget(
        self,
        annotation: Any,
        allowed_values: Optional[List[Any]] = None,
        default: Any = None,
    ) -> QLineEdit:
        line_edit = QLineEdit()
        int_validator = QIntValidator()
        int_validator.setBottom(0)  # Adjust as needed
        line_edit.setValidator(int_validator)
        if default is not None:
            line_edit.setText(str(default))
        return line_edit

    def get_value(self, widget: QWidget, annotation: Any) -> Optional[Any]:
        if not isinstance(widget, QLineEdit):
            logger.error(
                f"IntHandler.get_value: Expected QLineEdit, got {type(widget)}"
            )
            return None
        text = widget.text()
        try:
            value = int(text)
            logger.debug(f"Converted QLineEdit text '{text}' to int '{value}'")
            return value
        except ValueError:
            logger.error(f"Failed to convert '{text}' to int.")
            return None


# Handler for float types
class FloatHandler(TypeHandler):
    def create_widget(
        self,
        annotation: Any,
        allowed_values: Optional[List[Any]] = None,
        default: Any = None,
    ) -> QLineEdit:
        line_edit = QLineEdit()
        double_validator = QDoubleValidator()
        double_validator.setBottom(0.0)  # Adjust as needed
        line_edit.setValidator(double_validator)
        if default is not None:
            line_edit.setText(str(default))
        return line_edit

    def get_value(self, widget: QWidget, annotation: Any) -> Optional[Any]:
        if not isinstance(widget, QLineEdit):
            logger.error(
                f"FloatHandler.get_value: Expected QLineEdit, got {type(widget)}"
            )
            return None
        text = widget.text()
        try:
            value = float(text)
            logger.debug(f"Converted QLineEdit text '{text}' to float '{value}'")
            return value
        except ValueError:
            logger.error(f"Failed to convert '{text}' to float.")
            return None


# Handler for string types
class StrHandler(TypeHandler):
    def create_widget(
        self,
        annotation: Any,
        allowed_values: Optional[List[Any]] = None,
        default: Any = None,
    ) -> QLineEdit:
        line_edit = QLineEdit()
        if default is not None:
            line_edit.setText(default)
        return line_edit

    def get_value(self, widget: QWidget, annotation: Any) -> Optional[Any]:
        if not isinstance(widget, QLineEdit):
            logger.error(
                f"StrHandler.get_value: Expected QLineEdit, got {type(widget)}"
            )
            return None
        text = widget.text()
        logger.debug(f"QLineEdit text: {text}")
        return text


# Handler for list types
class ListHandler(TypeHandler):
    def create_widget(
        self,
        annotation: Any,
        allowed_values: Optional[List[Any]] = None,
        default: Any = None,
    ) -> QLineEdit:
        line_edit = QLineEdit()
        if default is not None and isinstance(default, list):
            line_edit.setText(",".join(map(str, default)))
        return line_edit

    def get_value(self, widget: QWidget, annotation: Any) -> Optional[Any]:
        if not isinstance(widget, QLineEdit):
            logger.error(
                f"ListHandler.get_value: Expected QLineEdit, got {type(widget)}"
            )
            return None
        text = widget.text()
        value = [item.strip() for item in text.split(",") if item.strip()]
        logger.debug(f"Converted QLineEdit text '{text}' to list '{value}'")
        return value


# Handler for Enum types
class EnumHandler(TypeHandler):
    def create_widget(
        self,
        annotation: Any,
        allowed_values: Optional[List[Any]] = None,
        default: Any = None,
    ) -> QComboBox:
        combo = QComboBox()
        combo.addItems([member.name for member in annotation])
        if default is not None and isinstance(default, Enum):
            combo.setCurrentText(default.name)
        return combo

    def get_value(self, widget: QWidget, annotation: Any) -> Optional[Any]:
        if not isinstance(widget, QComboBox):
            logger.error(
                f"EnumHandler.get_value: Expected QComboBox, got {type(widget)}"
            )
            return None
        current_text = widget.currentText()
        try:
            value = annotation[current_text]
            logger.debug(
                f"Converted QComboBox selection '{current_text}' to Enum '{value}'"
            )
            return value
        except KeyError:
            logger.warning(
                f"Enum conversion failed for value '{current_text}' in {annotation}"
            )
            return current_text  # Fallback to string if enum member not found


# Handler for boolean types
class BoolHandler(TypeHandler):
    def create_widget(
        self,
        annotation: Any,
        allowed_values: Optional[List[Any]] = None,
        default: Any = None,
    ) -> QCheckBox:
        checkbox = QCheckBox()
        if default is not None:
            checkbox.setChecked(bool(default))
        return checkbox

    def get_value(self, widget: QWidget, annotation: Any) -> Optional[Any]:
        if not isinstance(widget, QCheckBox):
            logger.error(
                f"BoolHandler.get_value: Expected QCheckBox, got {type(widget)}"
            )
            return None
        value = widget.isChecked()
        logger.debug(f"QCheckBox isChecked: {value}")
        return value


# Handler for ComboBox with allowed values (for non-Enum types)
class ComboBoxHandler(TypeHandler):
    def create_widget(
        self,
        annotation: Any,
        allowed_values: Optional[List[Any]] = None,
        default: Any = None,
    ) -> QComboBox:
        if allowed_values is None:
            raise ValueError("ComboBoxHandler.create_widget requires allowed_values")
        combo = QComboBox()
        combo.addItems([str(val) for val in allowed_values])
        if default is not None:
            combo.setCurrentText(str(default))
        return combo

    def get_value(self, widget: QWidget, annotation: Any) -> Optional[Any]:
        if not isinstance(widget, QComboBox):
            logger.error(
                f"ComboBoxHandler.get_value: Expected QComboBox, got {type(widget)}"
            )
            return None
        current_text = widget.currentText()
        try:
            if isinstance(annotation, type) and issubclass(annotation, Enum):
                value = annotation[current_text]
                logger.debug(
                    f"Converted QComboBox selection '{current_text}' to Enum '{value}'"
                )
                return value
            elif annotation == int:
                int_value = int(current_text)
                logger.debug(
                    f"Converted QComboBox selection '{current_text}' to int '{int_value}'"
                )
                return int_value
            elif annotation == float:
                float_value = float(current_text)
                logger.debug(
                    f"Converted QComboBox selection '{current_text}' to float '{float_value}'"
                )
                return float_value
            elif annotation == str:
                logger.debug(f"QComboBox selected value: {current_text}")
                return current_text
            elif getattr(annotation, "__origin__", None) == list:
                list_value = [
                    item.strip() for item in current_text.split(",") if item.strip()
                ]
                logger.debug(
                    f"Converted QComboBox selection '{current_text}' to list '{list_value}'"
                )
                return list_value
            else:
                logger.warning(f"Unsupported type '{annotation}' for ComboBoxHandler.")
                return current_text
        except (ValueError, KeyError) as e:
            logger.error(f"Failed to convert '{current_text}' to {annotation}: {e}")
            return None


# Registry mapping types to their handlers
TYPE_HANDLERS: Dict[Any, TypeHandler] = {
    int: IntHandler(),
    float: FloatHandler(),
    str: StrHandler(),
    list: ListHandler(),
    bool: BoolHandler(),
    # Enums are handled separately via ComboBoxHandler
}


class SetupPanel(QWidget):
    # Define a custom signal to emit the configured oscilloscope
    oscilloscope_configured = Signal(OScope)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.main_layout = QVBoxLayout()

        # Dictionary to hold method configurations
        # Key: method name, Value: dict of argument widgets
        self.method_configs: Dict[str, Dict[str, QWidget]] = {}

        # Dictionary to map widgets to their parameter types
        self.widget_to_type: Dict[QWidget, Any] = {}

        # Dropdown for oscilloscope types
        self.scope_type_combo = QComboBox()
        self.scope_type_combo.addItems([scope.__name__ for scope in scope_types])
        self.scope_type_combo.currentIndexChanged.connect(self.populate_init_config)

        # GroupBox for Oscilloscope Initialization (__init__ parameters)
        self.init_group_box = QGroupBox("Oscilloscope Initialization")
        self.init_layout = QFormLayout()
        self.init_group_box.setLayout(self.init_layout)

        # Dictionary to hold init parameter widgets
        self.init_params_widgets: Dict[str, QWidget] = {}

        # Scroll area for method configurations
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_content)

        # Initialize oscilloscope button
        self.init_run_button = QPushButton("Initialize Oscilloscope")
        self.init_run_button.clicked.connect(self.initialize_oscilloscope)

        # Add widgets to the main layout
        self.main_layout.addWidget(QLabel("Select Oscilloscope Type:"))
        self.main_layout.addWidget(self.scope_type_combo)
        self.main_layout.addWidget(self.init_group_box)
        self.main_layout.addWidget(
            self.init_run_button, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.main_layout.addWidget(QLabel("Configure Methods:"))
        self.main_layout.addWidget(self.scroll_area)

        self.setLayout(self.main_layout)

        # Initialize with the first scope
        self.populate_init_config(0)

        # Initialize the oscilloscope attribute
        self.oscilloscope: Optional[OScope] = None

    def populate_init_config(self, index: int) -> None:
        """
        Populate the initialization configuration based on the selected oscilloscope's __init__ parameters.
        """
        # Clear existing init parameter widgets
        while self.init_layout.count():
            child = self.init_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.init_params_widgets.clear()

        # Get selected oscilloscope class
        scope_class = scope_types[index]

        # Inspect __init__ method
        init_method = scope_class.__init__
        sig = inspect.signature(init_method)
        params = sig.parameters

        logger.debug(f"Configuring __init__ for {scope_class.__name__}")

        for name, param in params.items():
            if name == "self":
                continue  # Skip 'self' parameter

            param_type = param.annotation
            param_default = (
                param.default if param.default is not inspect.Parameter.empty else None
            )

            # Create widget based on parameter type
            widget = self.create_widget(
                param_type, allowed_values=None, default=param_default
            )

            # Add to layout
            self.init_layout.addRow(QLabel(f"{name}:"), widget)
            self.init_params_widgets[name] = widget

            # Map widget to its parameter type
            self.widget_to_type[widget] = param_type

            logger.debug(
                f"Added init parameter: {name} (type: {param_type}, default: {param_default})"
            )

    def initialize_oscilloscope(self) -> None:
        """
        Instantiate the oscilloscope with the provided __init__ parameters.
        Then, populate the method configurations.
        """
        index = self.scope_type_combo.currentIndex()
        scope_class = scope_types[index]

        # Prepare __init__ arguments
        init_kwargs = {}
        for name, widget in self.init_params_widgets.items():
            value = self.get_value(widget)
            if value is None:
                QMessageBox.warning(
                    self, "Invalid Input", f"Invalid value for parameter '{name}'."
                )
                return
            init_kwargs[name] = value

        logger.debug(
            f"Initializing oscilloscope {scope_class.__name__} with args: {init_kwargs}"
        )

        try:
            oscilloscope = scope_class(**init_kwargs)
        except Exception as e:
            logger.error(f"Failed to instantiate {scope_class.__name__}: {e}")
            QMessageBox.critical(
                self, "Initialization Error", f"Failed to initialize oscilloscope: {e}"
            )
            return

        logger.info(f"Successfully instantiated oscilloscope: {oscilloscope.idn}")

        # Store the oscilloscope instance
        self.oscilloscope = oscilloscope

        # Emit the oscilloscope instance
        self.oscilloscope_configured.emit(oscilloscope)

        # Populate method configurations
        self.populate_method_config(scope_class)

        QMessageBox.information(
            self,
            "Success",
            f"Oscilloscope {oscilloscope.idn} initialized successfully.",
        )

    def populate_method_config(self, scope_class: Type[OScope]) -> None:
        """
        Populate the method configurations based on the oscilloscope's methods.
        Each method will have its own QGroupBox with input widgets and a Run button.
        """
        # Clear existing method configurations
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.method_configs.clear()

        logger.debug(f"Populating method configurations for {scope_class.__name__}")

        # Inspect all callable members, including inherited ones
        for name, method in inspect.getmembers(
            scope_class, predicate=inspect.isroutine
        ):
            if name.startswith("_"):
                continue  # Skip private/protected methods
            if not callable(method):
                continue  # Ensure it's callable

            # Skip __init__, already handled
            if name == "__init__":
                continue

            # Get method signature
            sig = inspect.signature(method)
            params = sig.parameters

            # Exclude 'self' parameter
            args = [param for param in params.values() if param.name != "self"]

            # Create a QGroupBox for the method
            group_box = QGroupBox(name)
            group_layout = QFormLayout()

            # Dictionary to hold argument widgets for this method
            arg_widgets: Dict[str, QWidget] = {}

            # Check if the method has 'allowed_values' attribute from the decorator
            allowed_values = getattr(method, "allowed_values", {})

            for arg in args:
                arg_name = arg.name
                arg_annotation = arg.annotation
                arg_default = (
                    arg.default if arg.default is not inspect.Parameter.empty else None
                )

                # Determine if this argument has allowed values from the decorator
                if arg_name in allowed_values and allowed_values[arg_name]:
                    widget = self.create_widget(
                        annotation=arg_annotation,
                        allowed_values=allowed_values[arg_name],
                        default=arg_default,
                    )
                else:
                    # Determine widget based on type annotation
                    widget = self.create_widget(
                        annotation=arg_annotation,
                        allowed_values=None,
                        default=arg_default,
                    )

                group_layout.addRow(QLabel(arg_name + ":"), widget)
                arg_widgets[arg_name] = widget

                # Map widget to its parameter type
                self.widget_to_type[widget] = arg_annotation

                logger.debug(
                    f"Added method parameter: {name}.{arg_name} (type: {arg_annotation}, default: {arg_default})"
                )

            # Add Run button for the method
            run_button = QPushButton(f"Run {name}")
            # Use default arguments in lambda to capture current method and widgets
            run_button.clicked.connect(
                lambda checked, m=name, aw=arg_widgets: self.run_method(m, aw)
            )

            # Layout setup
            group_layout.addRow(run_button)
            group_box.setLayout(group_layout)
            self.scroll_layout.addWidget(group_box)

            # Store the argument widgets for this method
            self.method_configs[name] = arg_widgets

            logger.debug(
                f"Configured method: {name} with arguments: {list(arg_widgets.keys())}"
            )

        # Add stretch to push widgets to the top
        self.scroll_layout.addStretch()

    def run_method(self, method_name: str, args_widgets: Dict[str, QWidget]) -> None:
        """
        Execute a single method with the provided arguments.
        """
        oscilloscope = self.oscilloscope

        if oscilloscope is None:
            QMessageBox.warning(
                self, "No Oscilloscope", "Please initialize an oscilloscope first."
            )
            return

        # Prepare arguments
        kwargs = {}
        for arg_name, widget in args_widgets.items():
            value = self.get_value(widget)
            if value is None:
                QMessageBox.warning(
                    self, "Invalid Input", f"Invalid value for parameter '{arg_name}'."
                )
                return
            kwargs[arg_name] = value

        logger.debug(f"Running method {method_name} with arguments {kwargs}")

        # Call the method with arguments
        try:
            method = getattr(oscilloscope, method_name)
            method(**kwargs)
            QMessageBox.information(
                self, "Success", f"Method '{method_name}' executed successfully."
            )
            logger.info(f"Method '{method_name}' executed with arguments {kwargs}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Execution Error",
                f"Failed to execute method '{method_name}': {e}",
            )
            logger.error(f"Error executing method '{method_name}': {e}")

    def create_widget(
        self,
        annotation: Any,
        allowed_values: Optional[List[Any]] = None,
        default: Any = None,
    ) -> QWidget:
        """
        Create and return a widget based on the type annotation and allowed values.
        """
        if allowed_values:
            # Use ComboBoxHandler for parameters with allowed values
            combo_handler: TypeHandler = ComboBoxHandler()
            widget = combo_handler.create_widget(annotation, allowed_values, default)
            return widget
        elif isinstance(annotation, type) and issubclass(annotation, Enum):
            # Use EnumHandler for Enum types without allowed values
            enum_handler: TypeHandler = EnumHandler()
            widget = enum_handler.create_widget(annotation, default=default)
            return widget
        else:
            # Use appropriate TypeHandler based on annotation
            handler = TYPE_HANDLERS.get(annotation, StrHandler())
            widget = handler.create_widget(annotation, default=default)
            return widget

    def get_value(self, widget: QWidget) -> Optional[Any]:
        """
        Retrieve and convert the value from the widget based on its type.
        """
        param_type = self.widget_to_type.get(widget, None)

        if isinstance(widget, QComboBox):
            # Use ComboBoxHandler for ComboBox widgets
            combo_handler = ComboBoxHandler()
            return combo_handler.get_value(widget, param_type)
        elif isinstance(widget, QLineEdit):
            # Use appropriate TypeHandler based on param_type
            handler = TYPE_HANDLERS.get(param_type, StrHandler())
            return handler.get_value(widget, param_type)
        elif isinstance(widget, QCheckBox):
            # Use BoolHandler for CheckBox widgets
            bool_handler = TYPE_HANDLERS.get(bool, BoolHandler())
            return bool_handler.get_value(widget, bool)
        else:
            logger.error(f"Unsupported widget type: {type(widget)}")
            return None  # Unsupported widget type
