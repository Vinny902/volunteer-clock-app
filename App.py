from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.screen import Screen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import TwoLineListItem, MDList
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.widget import Widget
from datetime import datetime
import sqlite3

KV = '''
ScreenManager:
    MainScreen:

<MainScreen>:
    name: 'main'
    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: [0.97, 0.98, 0.99, 1]

        MDBoxLayout:
            size_hint_y: None
            height: dp(50)
            padding: dp(10)
            spacing: dp(20)
            md_bg_color: [0.36, 0.65, 0.82, 1]

            MDRaisedButton:
                text: "Employees"
                md_bg_color: [0.36, 0.65, 0.82, 1]
                text_color: [1, 1, 1, 1]
                on_release: app.show_employees()

            MDRaisedButton:
                text: "Time Entries"
                md_bg_color: [0.36, 0.65, 0.82, 1]
                text_color: [1, 1, 1, 1]
                on_release: app.show_time_entries()

            MDRaisedButton:
                text: "Reports"
                md_bg_color: [0.36, 0.65, 0.82, 1]
                text_color: [1, 1, 1, 1]
                on_release: app.show_reports()

        MDBoxLayout:
            id: realtime_clock_bar
            size_hint_y: None
            height: dp(30)
            padding: dp(10), 0
            spacing: dp(10)
            md_bg_color: [0.83, 0.94, 0.96, 1]

            MDLabel:
                id: clinic_title
                text: "Good Samaritan Clinic"
                halign: 'left'
                theme_text_color: "Custom"
                text_color: [0, 0, 0, 1]
                font_style: "Caption"
                size_hint_x: 0.5

            MDLabel:
                id: realtime_clock
                text: ""
                halign: 'right'
                theme_text_color: "Custom"
                text_color: [0, 0, 0, 1]
                font_style: "Caption"
                size_hint_x: 0.5

        MDBoxLayout:
            id: clockin_status_bar
            size_hint_y: None
            height: dp(30)
            padding: dp(10), 0
            spacing: dp(10)
            md_bg_color: [0.93, 0.97, 0.98, 1]
            opacity: 0

            MDLabel:
                id: clockin_status
                text: ""
                halign: "center"
                theme_text_color: "Custom"
                text_color: [0.1, 0.1, 0.1, 1]
                font_style: "Body2"

        MDBoxLayout:
            id: content_area
            orientation: 'vertical'
'''

class MainScreen(Screen):
    pass

class VerticalSeparator(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_x = None
        self.width = dp(1)
        with self.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(0, 0, 0, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        
        self.bind(pos=self.update_rect, size=self.update_rect)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class VolunteerApp(MDApp):
    dialog = None
    clock_in_time = None
    current_employee = None
    timer_event = None
    role_selected = None
    employee_name = None
    last_clicked_button = None

    employee_roles = [
        "APRN & PA", "Board Member", "Dental Assistant", "Dentist", "Doctor", "Student", "Reception", "Prayer Warrior"
    ]

    def build(self):
        self.theme_cls.material_style = "M3"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "DeepPurple"
        self.conn = sqlite3.connect("volunteer_app.db")
        self.create_tables()
        self.root = Builder.load_string(KV)

        self.realtime_label = self.root.get_screen('main').ids.realtime_clock
        self.clockin_status_label = self.root.get_screen('main').ids.clockin_status
        self.clockin_status_bar = self.root.get_screen('main').ids.clockin_status_bar

        Clock.schedule_interval(self.update_realtime_clock, 1)
        return self.root

    def create_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS employees (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        role TEXT NOT NULL
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS timesheets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id INTEGER,
                        clock_in TEXT,
                        clock_out TEXT,
                        FOREIGN KEY(employee_id) REFERENCES employees(id)
                    )''')
        self.conn.commit()

    def update_realtime_clock(self, *args):
        now = datetime.now().strftime("%I:%M:%S %p | %A, %B %d, %Y")
        self.realtime_label.text = now
        self.update_timer()

    def show_home(self):
        self.root.get_screen('main').ids.content_area.clear_widgets()
        
    def verify_boss_pin_for_add(self, *args):
        self.prompt_pin(lambda: self.add_employee_dialog())

    def prompt_pin(self, on_success_callback):
        layout = MDBoxLayout(orientation='vertical', spacing=20, padding=[20, 20, 20, 20], size_hint_y=None)
        layout.height = dp(120)

        pin_label = MDLabel(
            text="Enter 4-digit PIN", halign="left",
            theme_text_color="Custom", text_color=[0, 0, 0, 1],
            size_hint_y=None, height=dp(24)
        )

        pin_input = MDTextField(
            hint_text="PIN", password=True, input_filter="int",
            max_text_length=4, mode="rectangle"
        )

        layout.add_widget(pin_label)
        layout.add_widget(pin_input)

        def verify_pin(*_):
            if pin_input.text == "1234":  # Boss PIN
                self.dialog.dismiss()
                on_success_callback()
            else:
                pin_input.error = True
                pin_input.helper_text = "Incorrect PIN"

        self.dialog = MDDialog(
            title="Authorization Required",
            type="custom",
            content_cls=layout,
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(text="Submit", on_release=verify_pin)
            ]
        )
        self.dialog.open()

    def show_employees(self, *args):
        content = MDBoxLayout(orientation='vertical', spacing=10, padding=10)
        search_field = MDTextField(hint_text="Search employee name", on_text_validate=self.filter_employees)
        self.search_input = search_field
        self.employee_list_widget = MDBoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        self.employee_list_widget.bind(minimum_height=self.employee_list_widget.setter('height'))

        scroll = ScrollView()
        scroll.add_widget(self.employee_list_widget)

        content.add_widget(search_field)
        content.add_widget(scroll)
        content.add_widget(MDRaisedButton(text="Add Employee",md_bg_color=[0.36, 0.65, 0.82, 1],
        text_color=[1, 1, 1, 1], on_press=self.verify_boss_pin_for_add))

        self.root.get_screen('main').ids.content_area.clear_widgets()
        self.root.get_screen('main').ids.content_area.add_widget(content)

        self.load_employees()

    def filter_employees(self, *args):
        self.load_employees(filter_text=self.search_input.text.strip().lower())
        
    def load_employees(self, filter_text=""):
        self.employee_list_widget.clear_widgets()
        c = self.conn.cursor()
        c.execute("SELECT id, name, role FROM employees ORDER BY role, name")
        employees = c.fetchall()

        # Organize employees by role
        grouped = {role: [] for role in self.employee_roles}
        for emp_id, name, role in employees:
            if filter_text and filter_text not in name.lower():
                continue
            if role in grouped:
                grouped[role].append((emp_id, name))

        # Add header row
        header_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30), spacing=10)
        for idx, role in enumerate(self.employee_roles):
            col = MDBoxLayout(orientation="vertical", size_hint_x=None, width=dp(140))
            col.add_widget(MDLabel(
                text=role, halign="center", bold=True,
                theme_text_color="Custom", text_color=[0, 0, 0, 1]
            ))
            header_row.add_widget(col)

            # Add vertical line separator between columns
            if idx < len(self.employee_roles) - 1:
                header_row.add_widget(VerticalSeparator())

        self.employee_list_widget.add_widget(header_row)
        self.employee_list_widget.add_widget(Widget(size_hint_y=None, height=dp(10)))  # spacing

        # Determine the max number of people in any role to align rows
        max_count = max(len(v) for v in grouped.values())

        # Add rows of employee names
        for i in range(max_count):
            row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30), spacing=10)
            for idx, role in enumerate(self.employee_roles):
                col = MDBoxLayout(orientation="vertical", size_hint_x=None, width=dp(140))

                if i < len(grouped[role]):
                    emp_id, name = grouped[role][i]
                    label = MDLabel(
                        text=f"• {name}",
                        halign="left",
                        theme_text_color="Custom",
                        text_color=[0, 0, 0, 1],
                        font_style="Body1",
                        size_hint_y=None,
                        height=dp(30)
                    )
                    label.bind(
                        on_touch_down=lambda instance, touch, i=emp_id, n=name:
                        self.open_employee_menu(i, n, instance) if instance.collide_point(*touch.pos) else None
                    )
                    col.add_widget(label)
                else:
                    col.add_widget(MDLabel(text=""))  # blank space for alignment

                row.add_widget(col)

                if idx < len(self.employee_roles) - 1:
                    row.add_widget(VerticalSeparator())

            self.employee_list_widget.add_widget(row)

    def open_employee_menu(self, emp_id, name, caller_widget):
        self.last_clicked_button = caller_widget
        menu_items = [
            {"text": "Clock In", "viewclass": "OneLineListItem", "on_release": lambda: self.select_employee_action("clock_in", emp_id, name)},
            {"text": "Remove Employee", "viewclass": "OneLineListItem", "on_release": lambda: self.select_employee_action("remove", emp_id, name)},
        ]
        self.emp_menu = MDDropdownMenu(items=menu_items, width_mult=3, caller=self.last_clicked_button)
        self.emp_menu.open()

    def select_employee_action(self, action, emp_id, name):
        self.emp_menu.dismiss()
        if action == "clock_in":
            self.clock_in(emp_id, name)
        elif action == "remove":
            self.prompt_pin(lambda: self.remove_employee(emp_id))

    def remove_employee(self, emp_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
        self.conn.commit()
        self.show_employees()

    def add_employee_dialog(self, *args):
        layout = MDBoxLayout(orientation='vertical', spacing=15, padding=dp(20), size_hint_y=None)
        layout.height = self.root.height * 0.3

        name_label = MDLabel(text="Enter employee name:", halign="left", theme_text_color="Custom", text_color=[0, 0, 0, 1])
        self.name_input = MDTextField(hint_text="Full Name", mode="rectangle")
        self.role_menu_button = MDRaisedButton(text="Select Role", on_release=self.open_role_menu)

        layout.add_widget(name_label)
        layout.add_widget(self.name_input)
        layout.add_widget(self.role_menu_button)

        self.dialog = MDDialog(
            type="custom",
            content_cls=layout,
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(text="Save", on_release=lambda x: self.save_employee())
            ]
        )
        self.dialog.open()

    def open_role_menu(self, *args):
        menu_items = [{"text": role, "viewclass": "OneLineListItem", "on_release": lambda x=role: self.select_role(x)} for role in self.employee_roles]
        self.menu = MDDropdownMenu(caller=self.role_menu_button, items=menu_items, width_mult=4)
        self.menu.open()

    def select_role(self, role):
        self.role_selected = role
        self.role_menu_button.text = role
        self.menu.dismiss()

    def save_employee(self):
        name = self.name_input.text.strip()
        role = self.role_selected
        if not name or not role:
            alert = MDDialog(
                title="Missing Info",
                text="Please enter a name and select a role.",
                buttons=[MDRaisedButton(text="OK", on_release=lambda x: alert.dismiss())]
            )
            alert.open()
            return
        c = self.conn.cursor()
        c.execute("INSERT INTO employees (name, role) VALUES (?, ?)", (name, role))
        self.conn.commit()
        self.dialog.dismiss()
        self.show_employees()

    def clock_in(self, emp_id, name):
        self.clock_in_time = datetime.now()
        self.current_employee = emp_id
        self.employee_name = name
        c = self.conn.cursor()
        c.execute("INSERT INTO timesheets (employee_id, clock_in) VALUES (?, ?)", (emp_id, self.clock_in_time.isoformat()))
        self.conn.commit()
        self.clockin_status_bar.opacity = 1
        self.start_timer()

        if not hasattr(self, 'clockout_btn'):
            self.clockout_btn = MDRaisedButton(
                text="Clock Out",
                on_release=lambda x: self.clock_out(),
                size_hint=(None, None),
                size=(dp(90), dp(24)),
                pos_hint={"center_y": 0.5}
            )
            self.root.get_screen('main').ids.clockin_status_bar.add_widget(self.clockout_btn)
        else:
            self.clockout_btn.opacity = 1
            self.clockout_btn.disabled = False

    def clock_out(self):
        if self.clock_in_time:
            clock_out_time = datetime.now().isoformat()
            c = self.conn.cursor()
            c.execute('''UPDATE timesheets SET clock_out=? WHERE employee_id=? AND clock_out IS NULL''', (clock_out_time, self.current_employee))
            self.conn.commit()
            self.stop_timer()

    def start_timer(self):
        self.timer_event = Clock.schedule_interval(self.update_timer, 1)

    def stop_timer(self):
        if self.timer_event:
            Clock.unschedule(self.timer_event)
        self.timer_event = None
        self.clock_in_time = None
        self.current_employee = None
        self.employee_name = None
        self.clockin_status_bar.opacity = 0
        if hasattr(self, 'clockout_btn'):
            self.clockout_btn.opacity = 0
            self.clockout_btn.disabled = True

    def update_timer(self, *args):
        if self.clock_in_time:
            now = datetime.now()
            duration = now - self.clock_in_time
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            formatted = f"{hours:02}:{minutes:02}:{seconds:02}"
            self.clockin_status_label.text = f"{self.employee_name} clocked in | Duration: {formatted}"

    def show_time_entries(self):
        c = self.conn.cursor()
        c.execute('''SELECT e.name, e.role, t.clock_in, t.clock_out FROM timesheets t JOIN employees e ON e.id = t.employee_id ORDER BY t.clock_in DESC''')
        rows = c.fetchall()

        content = MDBoxLayout(orientation='vertical', spacing=10, padding=10)
        scroll = ScrollView()
        timesheet_list = MDList()

        for name, role, clock_in, clock_out in rows:
            clock_in_fmt = datetime.fromisoformat(clock_in).strftime('%I:%M:%S %p %A, %B %d, %Y') if clock_in else '---'
            clock_out_fmt = datetime.fromisoformat(clock_out).strftime('%I:%M:%S %p %A, %B %d, %Y') if clock_out else '---'
            timesheet_list.add_widget(TwoLineListItem(text=f"{name} ({role})", secondary_text=f"IN: {clock_in_fmt} | OUT: {clock_out_fmt}"))

        scroll.add_widget(timesheet_list)
        content.add_widget(scroll)
        self.root.get_screen('main').ids.content_area.clear_widgets()
        self.root.get_screen('main').ids.content_area.add_widget(content)

    def show_reports(self):
        self.show_time_entries()

if __name__ == '__main__':
    VolunteerApp().run()