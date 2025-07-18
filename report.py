from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox, QSpinBox, QTextEdit, QMessageBox,
    QPushButton, QVBoxLayout, QFormLayout, QTabWidget, QGridLayout, QApplication,
    QSpacerItem, QHBoxLayout, QDialog, QDialogButtonBox
)

from PyQt6.QtCore import QThreadPool, QRunnable, QObject, pyqtSignal, pyqtSlot

import textwrap

import sys
import os
import json

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS # type: ignore
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class WorkerSignals(QObject):
    error = pyqtSignal(str)
    file_saved_as = pyqtSignal(str)

class Generator(QRunnable):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            from datetime import datetime
            from reportlab.pdfgen.canvas import Canvas
            from reportlab.lib.pagesizes import landscape, letter
            from reportlab.lib.units import inch
            from reportlab.lib import colors
        
            data = self.data
            wage = float(data['wage'])
            today = datetime.today().strftime("%Y-%m-%d")

            outfile = f"contribution_report_{today}.pdf"
            canvas = Canvas(outfile, pagesize=landscape(letter))
            width, height = landscape(letter)

            canvas.drawImage(resource_path("logo.jpeg"), 0.5 * inch, height - 1.5 * inch, width = 10 * inch, height = 1.25 * inch)

            canvas.setFont("Helvetica-Bold", 16)
            canvas.drawString(1 * inch, height - 2 * inch, "Production Contribution Report")

            canvas.setFont("Helvetica", 12)
            canvas.drawString(1.5 * inch, height - 2.35 * inch, f"Name: {data['name']}")
            canvas.drawString(4.75 * inch, height - 2.35 * inch, f"Shift: {data['shift']}")
            canvas.drawString(8 * inch, height - 2.35 * inch, f"Date: {today}")

            headers = ["Line", "Run Type", "Qty", "Prc", "Ple", "Hrs", "Revenue", "Labor", "Contribution"]
            col_widths = [0.5, 2.75, 0.9, 1.0, 0.8, 0.8, 1.2, 1.0, 1.3]
            start_x = .5 * inch
            start_y = height - 2.85 * inch
            row_height = 0.4 * inch

            def draw_row(y, values, gray=False):
                x = start_x
                for i, val in enumerate(values):
                    canvas.setFillColor(colors.grey if gray else colors.black)
                    canvas.drawString(x + 5, y + 5, str(val))
                    x += col_widths[i] * inch
                canvas.setFillColor(colors.black)

            draw_row(start_y, headers)

            total_revenue = 0.0
            total_labor = 0.0
            line_y = start_y - row_height
            
            with open(resource_path("settings.json"), "r", encoding="utf-8") as f:
                settings = json.load(f)
    
            prices = settings.get('prices', {})
            handpack_prices = settings.get('handpacks', {})

            for line in ['AZ', 'BZ', 'DZ', 'EZ', 'FZ', 'H1', 'H2']:
                entry = data['lines'].get(line, {})
                ltype = entry.get('type', '')
                qty = entry.get('qty', '')
                try: 
                    qty_val = int(qty) if qty else 0
                except (ValueError, TypeError): 
                    qty_val = 0

                if line in ['H1', 'H2']:
                    price = handpack_prices.get(ltype, 0.0)
                elif line in prices:
                    # Get threshold from settings or default to 5000
                    threshold = settings.get('qty_threshold', 5000)
                    price = prices[line][0] if qty_val > threshold else prices[line][1]
                else:
                    price = 0.0

                people = entry.get('ple', 0)
                hours = entry.get('hrs', 0)

                revenue = qty_val * price
                labor = hours * people * wage
                contribution = revenue - labor

                if qty_val > 0:
                    total_revenue += revenue
                    total_labor += labor
                draw_row(
                    line_y,
                    [line, ltype, qty_val if qty else "", f"{price:.4f}" if qty else "", people, hours,
                    f"${revenue:.2f}" if qty else "", f"${labor:.2f}" if qty else "", f"${contribution:.2f}"],
                    gray=(qty_val == 0)
                )
                line_y -= row_height
                
                # Add spacer after machine lines (FZ) and before handpack lines (H1)
                if line == 'FZ':
                    line_y -= row_height * 0.5  # Add half a row height as spacer

            canvas.setFont("Helvetica-Bold", 12)
            canvas.drawString(start_x, line_y - 10, f"Total Revenue: ${total_revenue:.2f}")
            canvas.drawString(start_x + 3.5 * inch, line_y - 10, f"Total Labor: ${total_labor:.2f}")
            canvas.drawString(start_x + 6.5 * inch, line_y - 10, f"Total Contribution: ${total_revenue - total_labor:.2f}")

            canvas.setFont("Helvetica", 11)
            canvas.drawString(start_x, line_y - 40, "Notes:")
            canvas.setFont("Helvetica-Oblique", 10)

            text = canvas.beginText(start_x, line_y - 60)
            text.setLeading(14)
            notes = data.get('notes', '').strip()
            if notes:
                wrapped = textwrap.wrap(notes, width=160)
                for line in wrapped[:5]:
                    text.textLine(line)
            else:
                text.textLine("No notes provided")
            canvas.drawText(text)

            canvas.save()
        except Exception as e:
            self.signals.error.emit(str(e))
            return
        self.signals.file_saved_as.emit(outfile)

class Report(QWidget):
    def __init__(self):
        super().__init__()

        self.settings_file = resource_path("settings.json")
        self.default_settings = {
            "wage": 10.00,
            "qty_threshold": 5000,
            "recent_names": [],
            "prices": {
                "AZ": [0.235, 0.382],
                "BZ": [0.257, 0.471],
                "DZ": [0.268, 0.530],
                "EZ": [0.331, 0.535],
                "FZ": [0.407, 0.637]
            }
        }
        self.settings = self.load_settings()

        VERSION = "v1.3.1"
        self.setWindowTitle(f"Daily Report Generator {VERSION}")
        self.threadpool = QThreadPool()
        self.line_fields = {}

        self.tabs = QTabWidget()

        # === Tab 1: Report ===
        self.name = QComboBox()
        self.name.setEditable(True)
        self.name.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.name.setMaxVisibleItems(8)  # Show up to 8 items in dropdown
        self.name.lineEdit().setPlaceholderText("Enter your full name") # type: ignore
        self.name.setFixedWidth(200)  # Set reasonable width for names
        
        # Load recent names
        recent_names = self.settings.get('recent_names', [])
        if recent_names:
            self.name.addItems(recent_names)
        
        self.shift = QSpinBox()
        self.shift.setRange(1, 2)
        self.shift.setFixedWidth(80)  # Set small width for shift (just 1-2)
        self.notes = QTextEdit()

        grid = QGridLayout()
        headers = ["Line", "Run Type", "Qty", "Ple", "Hrs"]
        for col, header in enumerate(headers):
            grid.addWidget(QLabel(header), 0, col)
            grid.setColumnMinimumWidth(col, 50)

        line_order = ['AZ', 'BZ', 'DZ', 'EZ', 'FZ', 'H1', 'H2']
        for row, line in enumerate(line_order, 1):
            self.line_fields[line] = {}
            grid.addWidget(QLabel(line), row, 0)
            grid.setColumnMinimumWidth(col, 50)
            
            handpack_names = list(self.settings.get("handpacks", {}).keys())
            handpack_options = ["Not Run"] + handpack_names

            type_options = {
                'AZ': ["Not Run", "Rotary", "Shuttle"],
                'BZ': ["Not Run", "Rotary", "Shuttle"],
                'DZ': ["Not Run", "Carousel/Rotary", "Shuttle"],
                'EZ': ["Not Run", "Rotary", "Shuttle"],
                'FZ': ["Not Run", "Rotary", "Shuttle"],
                'H1': handpack_options,
                'H2': handpack_options
            }

            options = type_options.get(line, ["Not Run"])

            type_box = QComboBox()
            type_box.addItems(options)
            qty_box = QLineEdit()
            ple_spin = QSpinBox()
            ple_spin.setRange(0, 20)
            hrs_spin = QSpinBox()
            hrs_spin.setRange(0, 8)

            def toggle_fields(text, qty=qty_box, ppl=ple_spin, hrs=hrs_spin):
                enabled = text != "Not Run"
                qty.setEnabled(enabled)
                ppl.setEnabled(enabled)
                hrs.setEnabled(enabled)

            type_box.currentTextChanged.connect(toggle_fields)
            toggle_fields(type_box.currentText()) 

            self.line_fields[line]['type'] = type_box
            self.line_fields[line]['qty'] = qty_box
            self.line_fields[line]['ple'] = ple_spin
            self.line_fields[line]['hrs'] = hrs_spin

            grid.addWidget(type_box, row, 1)
            grid.addWidget(qty_box, row, 2)
            grid.addWidget(ple_spin, row, 3)
            grid.addWidget(hrs_spin, row, 4)

        input_layout = QVBoxLayout()
        
        # Create horizontal layout for name and shift
        name_shift_layout = QHBoxLayout()
        name_shift_layout.addWidget(QLabel("Name"))
        name_shift_layout.addWidget(self.name)
        name_shift_layout.addStretch()  # Add stretch to push shift to the right
        name_shift_layout.addWidget(QLabel("Shift"))
        name_shift_layout.addWidget(self.shift)
        
        input_layout.addLayout(name_shift_layout)
        input_layout.addItem(QSpacerItem(0, 20))
        input_layout.addWidget(QLabel("Production Lines Running"))
        input_layout.addLayout(grid)
        input_layout.addItem(QSpacerItem(0, 20))
        input_layout.addWidget(QLabel("Notes"))
        input_layout.addWidget(self.notes)

        self.generate_btn = QPushButton("Generate PDF")
        self.generate_btn.clicked.connect(self.generate)
        input_layout.addWidget(self.generate_btn)

        input_tab = QWidget()
        input_tab.setLayout(input_layout)
        self.tabs.addTab(input_tab, "Report")

        # === Tab 2: Settings ===
        self.wage_input = QLineEdit()

        self.wage_input.setText(str(self.settings.get('wage', 10.00)))
        
        self.machine_fields = {}
        self.handpack_fields = {}

        machine_layout = QGridLayout()
        machine_layout.addWidget(QLabel("Line"), 0, 0)
        
        # Get threshold from settings or default to 5000
        self.qty_threshold = self.settings.get('qty_threshold', 5000)
        threshold_label = f"Over {self.qty_threshold}"
        under_threshold_label = f"Under {self.qty_threshold}"
        
        machine_layout.addWidget(QLabel(threshold_label), 0, 1)
        machine_layout.addWidget(QLabel(under_threshold_label), 0, 2)

        for i, line in enumerate(['AZ', 'BZ', 'DZ', 'EZ', 'FZ']):
            machine_layout.addWidget(QLabel(line), i + 1, 0)
            over = QLineEdit()
            under = QLineEdit()
            
            # Make price fields read-only
            over.setReadOnly(True)
            under.setReadOnly(True)
            
            self.machine_fields[line] = (over, under)
            machine_layout.addWidget(over, i + 1, 1)
            machine_layout.addWidget(under, i + 1, 2)
        
        
        for line, (over_field, under_field) in self.machine_fields.items():
            if line in self.settings.get('prices', {}):
                over, under = self.settings['prices'][line]
                over_field.setText(f"{over:.4f}")
                under_field.setText(f"{under:.4f}")
        
        # Create machine price control buttons
        machine_button_layout = QHBoxLayout()
        
        edit_machine_button = QPushButton("Edit Machine Prices")
        edit_threshold_button = QPushButton("Edit Quantity Threshold")
        
        edit_machine_button.clicked.connect(self.show_edit_machine_dialog)
        edit_threshold_button.clicked.connect(self.show_edit_threshold_dialog)
        
        machine_button_layout.addWidget(edit_machine_button)
        machine_button_layout.addWidget(edit_threshold_button)
        
        # Add machine button layout to settings
        machine_layout.addLayout(machine_button_layout, 6, 0, 1, 3)  # Span all columns
                
        handpack_layout = QVBoxLayout()        
        self.handpack_container = QVBoxLayout()
        
        self.handpack_widget = None
        
        for name, price in self.settings.get('handpacks', {}).items():
            self.add_handpack_field(name, price)
            
        self.handpack_widget = QWidget()
        self.handpack_widget.setLayout(self.handpack_container)
        handpack_layout.addWidget(self.handpack_widget)
        
        button_layout = QHBoxLayout()
        
        add_button = QPushButton("Add Hand Pack")
        edit_button = QPushButton("Edit Hand Pack")
        delete_button = QPushButton("Delete Hand Pack")
        
        add_button.clicked.connect(self.show_add_handpack_dialog)
        edit_button.clicked.connect(self.show_edit_handpack_dialog)
        delete_button.clicked.connect(self.show_delete_handpack_dialog)
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        
        handpack_layout.addLayout(button_layout)

        settings_layout = QFormLayout()
        settings_layout.addRow(QLabel("Average Wage ($/hr)"))
        settings_layout.addRow(self.wage_input)
        settings_layout.addItem(QSpacerItem(0, 20))
        
        settings_layout.addRow(QLabel("Machine Price:"))
        settings_layout.addRow(machine_layout)
        settings_layout.addItem(QSpacerItem(0, 20))
        
        settings_layout.addRow(QLabel("Hand Pack Price:"))
        settings_layout.addRow(handpack_layout)
        

        settings_tab = QWidget()
        settings_tab.setLayout(settings_layout)
        self.tabs.addTab(settings_tab, "Settings")

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    def add_handpack_field(self, name, price):
        layout = QHBoxLayout()
        name_label = QLabel(name)
        price_field = QLineEdit(f"{price:.4f}")
        
        price_field.setFixedWidth(100)
        price_field.setReadOnly(True)  # Make price field read-only
        
        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(price_field)
        self.handpack_container.addLayout(layout)
        self.handpack_fields[name] = price_field
        
        self.settings['handpacks'][name] = float(price)
        
        with open(resource_path("settings.json"), 'w') as f:
            json.dump(self.settings, f, indent=2)
            
    def add_handpack_field_to_container(self, name, price, container):
        layout = QHBoxLayout()
        name_label = QLabel(name)
        price_field = QLineEdit(f"{price:.4f}")
        
        price_field.setFixedWidth(100)
        price_field.setReadOnly(True)  # Make price field read-only
        
        layout.addWidget(name_label)
        layout.addStretch() 
        layout.addWidget(price_field)
        container.addLayout(layout)
        self.handpack_fields[name] = price_field
        
        self.settings['handpacks'][name] = float(price)
        
        with open(resource_path("settings.json"), 'w') as f:
            json.dump(self.settings, f, indent=2)
            
    def show_add_handpack_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Hand Pack")
        
        name_input = QLineEdit()
        price_input = QLineEdit()
        
        form_layout = QFormLayout()
        form_layout.addRow("Name:", name_input)
        form_layout.addRow("Price:", price_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        dialog.setLayout(layout)
        
        if dialog.exec():
            name = name_input.text().strip()
            try:
                price = float(price_input.text())
            except ValueError:
                return
            
            if name and name not in self.handpack_fields:
                self.settings['handpacks'][name] = price
                self.add_handpack_field(name, price)
                self.refresh_handpack()
                
    def show_edit_handpack_dialog(self):
        if not self.handpack_fields:
            QMessageBox.information(self, "No Hand Packs", "No hand packs available to edit.")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Hand Pack")
        
        name_combo = QComboBox()
        name_combo.addItems(list(self.handpack_fields.keys()))
        price_input = QLineEdit()
        
        if name_combo.count() > 0:
            current_name = name_combo.currentText()
            price_input.setText(str(self.handpack_fields[current_name].text()))
        
        # Update price when name changes
        def update_price():
            current_name = name_combo.currentText()
            price_input.setText(str(self.handpack_fields[current_name].text()))
        
        name_combo.currentTextChanged.connect(update_price)
        
        form_layout = QFormLayout()
        form_layout.addRow("Name:", name_combo)
        form_layout.addRow("Price:", price_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        dialog.setLayout(layout)
        
        if dialog.exec():
            name = name_combo.currentText()
            try:
                new_price = float(price_input.text())
                self.handpack_fields[name].setText(f"{new_price:.4f}")
                self.settings['handpacks'][name] = new_price
                with open(resource_path("settings.json"), 'w') as f:
                    json.dump(self.settings, f, indent=2)
                self.rebuild_handpack_section()
                self.refresh_handpack()
            except ValueError:
                QMessageBox.warning(self, "Invalid Price", "Please enter a valid number for the price.")
                
    def show_delete_handpack_dialog(self):
        if not self.handpack_fields:
            QMessageBox.information(self, "No Hand Packs", "No hand packs available to delete.")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Delete Hand Pack")
        
        name_combo = QComboBox()
        name_combo.addItems(list(self.handpack_fields.keys()))
        
        form_layout = QFormLayout()
        form_layout.addRow("Select Hand Pack to Delete:", name_combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        dialog.setLayout(layout)
        
        if dialog.exec():
            name = name_combo.currentText()
            reply = QMessageBox.question(self, "Confirm Delete", 
                                       f"Are you sure you want to delete '{name}'?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                if name in self.settings['handpacks']:
                    del self.settings['handpacks'][name]
                
                if name in self.handpack_fields:
                    del self.handpack_fields[name]
                
                with open(resource_path("settings.json"), 'w') as f:
                    json.dump(self.settings, f, indent=2)
                
                self.handpack_fields.clear()
                
                self.rebuild_handpack_section()
                
                self.refresh_handpack()
                
    def rebuild_handpack_section(self):
        self.handpack_fields.clear()
        
        if hasattr(self, 'handpack_widget') and self.handpack_widget:
            self.handpack_widget.hide()
        
        new_container = QVBoxLayout()
        
        for name, price in self.settings.get('handpacks', {}).items():
            self.add_handpack_field_to_container(name, price, new_container)
        
        new_widget = QWidget()
        new_widget.setLayout(new_container)
        
        if hasattr(self, 'handpack_widget') and self.handpack_widget:
            parent = self.handpack_widget.parent()
            if parent and parent.layout(): # type: ignore
                parent.layout().replaceWidget(self.handpack_widget, new_widget)  # type: ignore
                self.handpack_widget.deleteLater()
        
        self.handpack_widget = new_widget
        self.handpack_container = new_container
        
        self.handpack_widget.show()
        
        QApplication.processEvents()
                
    def show_edit_machine_dialog(self):
        if not self.machine_fields:
            QMessageBox.information(self, "No Machine Lines", "No machine lines available to edit.")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Machine Prices")
        dialog.setMinimumWidth(400)
        
        # Create form layout
        form_layout = QFormLayout()
        
        # Line selection
        line_combo = QComboBox()
        line_combo.addItems(['AZ', 'BZ', 'DZ', 'EZ', 'FZ'])
        
        # Price inputs
        over_price_input = QLineEdit()
        under_price_input = QLineEdit()
        
        # Set initial values
        if line_combo.count() > 0:
            current_line = line_combo.currentText()
            if current_line in self.machine_fields:
                over_field, under_field = self.machine_fields[current_line]
                over_price_input.setText(over_field.text())
                under_price_input.setText(under_field.text())
        
        # Update prices when line changes
        def update_prices():
            current_line = line_combo.currentText()
            if current_line in self.machine_fields:
                over_field, under_field = self.machine_fields[current_line]
                over_price_input.setText(over_field.text())
                under_price_input.setText(under_field.text())
        
        line_combo.currentTextChanged.connect(update_prices)
        
        # Add fields to form
        form_layout.addRow("Line:", line_combo)
        form_layout.addRow(f"Over {self.qty_threshold}:", over_price_input)
        form_layout.addRow(f"Under {self.qty_threshold}:", under_price_input)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        # Main layout
        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        dialog.setLayout(layout)
        
        if dialog.exec():
            line = line_combo.currentText()
            try:
                over_price = float(over_price_input.text())
                under_price = float(under_price_input.text())
                
                # Update the fields
                if line in self.machine_fields:
                    over_field, under_field = self.machine_fields[line]
                    over_field.setText(f"{over_price:.4f}")
                    under_field.setText(f"{under_price:.4f}")
                
                # Update settings
                if 'prices' not in self.settings:
                    self.settings['prices'] = {}
                self.settings['prices'][line] = [over_price, under_price]
                
                with open(resource_path("settings.json"), 'w') as f:
                    json.dump(self.settings, f, indent=2)
                    
            except ValueError:
                QMessageBox.warning(self, "Invalid Price", "Please enter valid numbers for the prices.")
                
    def show_edit_threshold_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Quantity Threshold")
        
        threshold_input = QLineEdit(str(self.qty_threshold))
        
        form_layout = QFormLayout()
        form_layout.addRow("Quantity Threshold:", threshold_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        dialog.setLayout(layout)
        
        if dialog.exec():
            try:
                new_threshold = int(threshold_input.text())
                if new_threshold > 0:
                    self.qty_threshold = new_threshold
                    self.settings['qty_threshold'] = new_threshold
                    
                    with open(resource_path("settings.json"), 'w') as f:
                        json.dump(self.settings, f, indent=2)
                    
                    # Update the labels in the machine layout
                    self.update_machine_labels()
                else:
                    QMessageBox.warning(self, "Invalid Threshold", "Threshold must be greater than 0.")
            except ValueError:
                QMessageBox.warning(self, "Invalid Threshold", "Please enter a valid number for the threshold.")
                
    def update_machine_labels(self):
        # Update the threshold labels in the machine layout
        threshold_label = f"Over {self.qty_threshold}"
        under_threshold_label = f"Under {self.qty_threshold}"
        
        # Try to find and update the labels in the machine layout
        try:
            settings_tab = self.tabs.widget(1)  # Settings tab is index 1
            if settings_tab and settings_tab.layout():
                for i in range(settings_tab.layout().count()): # type: ignore
                    item = settings_tab.layout().itemAt(i) # type: ignore
                    if hasattr(item, 'layout') and item.layout(): # type: ignore
                        if item.layout().itemAt(0) and hasattr(item.layout().itemAt(0), 'widget'): # type: ignore
                            first_widget = item.layout().itemAt(0).widget() # type: ignore
                            if first_widget and first_widget.text() == "Line": # type: ignore
                                if item.layout().itemAt(1) and hasattr(item.layout().itemAt(1), 'widget'): # type: ignore
                                    over_label = item.layout().itemAt(1).widget() # type: ignore
                                    if over_label:
                                        over_label.setText(threshold_label) # type: ignore
                                if item.layout().itemAt(2) and hasattr(item.layout().itemAt(2), 'widget'): # type: ignore
                                    under_label = item.layout().itemAt(2).widget() # type: ignore
                                    if under_label:
                                        under_label.setText(under_threshold_label) # type: ignore
                                break
        except:
            pass
        
        QMessageBox.information(self, "Threshold Updated", 
                              f"Quantity threshold updated to {self.qty_threshold}.")
                              
    def add_recent_name(self, name):
        """Add a name to the recent names list and update the combo box"""
        if not name or not name.strip():
            return
            
        name = name.strip()
        recent_names = self.settings.get('recent_names', [])
        
        # Remove the name if it already exists (to move it to the top)
        if name in recent_names:
            recent_names.remove(name)
        
        # Add the name to the beginning of the list
        recent_names.insert(0, name)
        
        # Keep only the last 10 names
        recent_names = recent_names[:10]
        
        # Update settings
        self.settings['recent_names'] = recent_names
        
        # Update the combo box
        self.name.clear()
        if recent_names:
            self.name.addItems(recent_names)
        
        # Save to file
        with open(resource_path("settings.json"), 'w') as f:
            json.dump(self.settings, f, indent=2)
                
    def refresh_handpack(self):
        handpack_names = ["Not Run"] + list(self.settings["handpacks"].keys())
        for line in ['H1', 'H2']:
            combo = self.line_fields[line]['type']
            current_value = combo.currentText()
            combo.clear()
            combo.addItems(handpack_names)

            if current_value in handpack_names:
                combo.setCurrentIndex(handpack_names.index(current_value))


    def load_settings(self):
        if os.path.exists(resource_path("settings.json")):
            with open(resource_path("settings.json"), 'r') as f:
                return json.load(f)
        else:
            return self.default_settings.copy()

    def generate(self):
        # Basic validation
        name = self.name.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Missing Information", "Please enter your full name.")
            return
            
        self.generate_btn.setDisabled(True)

        line_data = {}
        for line, fields in self.line_fields.items():
            line_data[line] = {
                'type': fields['type'].currentText(),
                'qty': fields['qty'].text(),
                'ple': fields['ple'].value(),
                'hrs': fields['hrs'].value()
            }
        
        try:
            wage = float(self.wage_input.text())
            if wage <= 0:
                QMessageBox.warning(self, "Invalid Wage", "Please enter a valid wage greater than 0.")
                self.generate_btn.setDisabled(False)
                return
        except ValueError:
            QMessageBox.warning(self, "Invalid Wage", "Please enter a valid number for the wage.")
            self.generate_btn.setDisabled(False)
            return

        prices = {}
        for line, (over_field, under_field) in self.machine_fields.items():
            try:
                over = float(over_field.text())
                under = float(under_field.text())
            except ValueError:
                over, under = 0.000, 0.000
            prices[line] = [over, under]
        
        data = {
            'name': name,
            'shift': str(self.shift.value()),
            'lines': line_data,
            'notes': self.notes.toPlainText(),
            'wage': wage,
            'prices': prices
        }
        
        # Add the name to recent names
        self.add_recent_name(name)

        self.settings['wage'] = float(self.wage_input.text())

        # Save machine prices
        for line, (over_field, under_field) in self.machine_fields.items():
            try:
                over = float(over_field.text())
                under = float(under_field.text())
                self.settings['prices'][line] = [over, under]
            except ValueError:
                continue  # skip bad entries

        # Save handpacks
        self.settings['handpacks'] = {}
        for name, field in self.handpack_fields.items():
            try:
                self.settings['handpacks'][name] = float(field.text())
            except ValueError:
                continue

        with open(resource_path("settings.json"), 'w') as f:
            json.dump(self.settings, f, indent=2)

        g = Generator(data)
        g.signals.file_saved_as.connect(self.generated)
        g.signals.error.connect(print)
        self.threadpool.start(g)

    def generated(self, outfile):
        self.generate_btn.setDisabled(False)
        try:
            os.startfile(outfile)
        except Exception as e:
            QMessageBox.information(self, "Finished", f"PDF has been generated: {outfile}")

app = QApplication([])
r = Report()
r.show()
app.exec()
