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
from kivymd.uix.gridlayout import MDGridLayout
from kivy.graphics import Color, Line, Rectangle 
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.widget import Widget
from datetime import datetime, timedelta
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

class BorderedBox(MDBoxLayout):
    def __init__(self, bg_color=(1, 1, 1, 1), **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        with self.canvas.before:
            Color(*self.bg_color)  # background color
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            Color(0, 0, 0, 1)  # black border
            self.border = Line(rectangle=(self.x, self.y, self.width, self.height), width=1)
        self.bind(pos=self.update_border, size=self.update_border)

    def update_border(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border.rectangle = (self.x, self.y, self.width, self.height)


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
        self.theme_cls.primary_palette = "LightBlue"
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
        
        # Title with search field
        title_box = MDBoxLayout(
            orientation='horizontal', 
            size_hint_y=None, 
            height=dp(50),
            spacing=10
        )
        
        title_label = MDLabel(
            text="Employees",
            font_style="H5",
            theme_text_color="Custom",
            text_color=[0.2, 0.2, 0.2, 1],
            size_hint_x=0.3
        )
        title_box.add_widget(title_label)
        
        search_field = MDTextField(
            hint_text="Search employee name",
            mode="rectangle",
            size_hint_x=0.7,
            on_text_validate=self.filter_employees
        )
        self.search_input = search_field
        title_box.add_widget(search_field)
        
        content.add_widget(title_box)
        
        # List view to display employees
        scroll = ScrollView()
        self.employee_list_widget = MDBoxLayout(
            orientation='vertical', 
            spacing=8, 
            size_hint_y=None,
            padding=[0, 5, 0, 5]
        )
        self.employee_list_widget.bind(minimum_height=self.employee_list_widget.setter('height'))
        scroll.add_widget(self.employee_list_widget)
        content.add_widget(scroll)
        
        # Add Employee button at the bottom
        add_button = MDRaisedButton(
            text="Add Employee",
            md_bg_color=[0.36, 0.65, 0.82, 1],
            text_color=[1, 1, 1, 1], 
            on_press=self.add_employee_dialog,
            size_hint=(None, None),
            size=(dp(150), dp(50)),
            pos_hint={"center_x": 0.5}
        )
        button_container = MDBoxLayout(
            size_hint_y=None, 
            height=dp(60), 
            padding=[0, 10, 0, 0]
        )
        button_container.add_widget(MDBoxLayout())  # Spacer
        button_container.add_widget(add_button)
        button_container.add_widget(MDBoxLayout())  # Spacer
        
        content.add_widget(button_container)
        
        self.root.get_screen('main').ids.content_area.clear_widgets()
        self.root.get_screen('main').ids.content_area.add_widget(content)
        
        self.load_employees()
    
    def filter_employees(self, *args):
        self.load_employees(filter_text=self.search_input.text.strip().lower())
        
    def load_employees(self, filter_text=""):
        self.employee_list_widget.clear_widgets()
        c = self.conn.cursor()
        
        # First, get all active clock-ins to check which employees are currently clocked in
        c.execute('''
            SELECT employee_id FROM timesheets 
            WHERE clock_out IS NULL
        ''')
        active_employees = {row[0] for row in c.fetchall()}
        
        # Fetch all employees
        c.execute("SELECT id, name, role FROM employees ORDER BY role, name")
        employees = c.fetchall()
        
        # Create a dictionary to group employees by role
        role_groups = {}
        
        # Filter and group employees
        for emp_id, name, role in employees:
            if filter_text and filter_text not in name.lower():
                continue
                
            if role not in role_groups:
                role_groups[role] = []
            
            role_groups[role].append((emp_id, name))
        
        # Display employees grouped by role
        for role in self.employee_roles:
            if role in role_groups and role_groups[role]:
                # Create role header
                role_header = MDBoxLayout(
                    orientation="horizontal",
                    size_hint_y=None,
                    height=dp(40),
                    padding=[10, 0, 10, 0],
                    spacing=10,
                    md_bg_color=[0.36, 0.65, 0.82, 1]  # Blue header
                )
                
                role_icon = MDBoxLayout(
                    size_hint=(None, None),
                    size=(dp(30), dp(30)),
                    md_bg_color=[1, 1, 1, 0.2],  # Slight white overlay
                    radius=[15, 15, 15, 15]  # Circle
                )
                
                role_label = MDLabel(
                    text=role,
                    theme_text_color="Custom",
                    text_color=[1, 1, 1, 1],  # White text
                    bold=True
                )
                
                count_label = MDLabel(
                    text=f"{len(role_groups[role])}",
                    theme_text_color="Custom",
                    text_color=[1, 1, 1, 0.8],  # Slightly transparent white
                    size_hint_x=None,
                    width=dp(30),
                    halign="right"
                )
                
                role_header.add_widget(role_icon)
                role_header.add_widget(role_label)
                role_header.add_widget(count_label)
                
                self.employee_list_widget.add_widget(role_header)
                
                # Display employees in this role
                for i, (emp_id, name) in enumerate(role_groups[role]):
                    # Create an employee card with ripple effect
                    employee_card = MDBoxLayout(
                        orientation="horizontal",
                        size_hint_y=None,
                        height=dp(60),
                        padding=[15, 5, 15, 5],
                        md_bg_color=[0.95, 0.95, 0.95, 1] if i % 2 == 0 else [1, 1, 1, 1]  # Alternating colors
                    )
                    
                    # Left side: Employee initials circle
                    initials = "".join([n[0].upper() for n in name.split() if n])
                    if not initials:
                        initials = "?"
                    
                    # Generate a deterministic color based on name
                    name_hash = sum(ord(c) for c in name)
                    r = (name_hash % 100) / 150 + 0.3  # 0.3-0.97
                    g = ((name_hash // 100) % 100) / 150 + 0.3  # 0.3-0.97
                    b = ((name_hash // 10000) % 100) / 150 + 0.3  # 0.3-0.97
                    
                    initials_box = MDBoxLayout(
                        orientation="vertical",
                        size_hint=(None, None),
                        size=(dp(40), dp(40)),
                        md_bg_color=[r, g, b, 1],
                        radius=[20, 20, 20, 20],  # Circle
                        pos_hint={"center_y": 0.5}
                    )
                    
                    initials_label = MDLabel(
                        text=initials,
                        halign="center",
                        valign="middle",
                        theme_text_color="Custom",
                        text_color=[1, 1, 1, 1],
                        font_style="H6"
                    )
                    initials_box.add_widget(initials_label)
                    
                    # Middle: Employee name and role
                    info_box = MDBoxLayout(
                        orientation="vertical",
                        padding=[10, 0, 0, 0],
                        size_hint_x=0.7
                    )
                    
                    name_label = MDLabel(
                        text=name,
                        theme_text_color="Custom",
                        text_color=[0.1, 0.1, 0.1, 1],
                        font_style="Subtitle1"
                    )
                    
                    role_label = MDLabel(
                        text=role,
                        theme_text_color="Custom",
                        text_color=[0.5, 0.5, 0.5, 1],
                        font_style="Caption"
                    )
                    
                    info_box.add_widget(name_label)
                    info_box.add_widget(role_label)
                    
                    # Right: Action buttons
                    action_box = MDBoxLayout(
                        orientation="horizontal",
                        size_hint_x=0.3,
                        spacing=5,
                        padding=[0, 0, 0, 0]
                    )
                    
                    # Check if employee is already clocked in
                    is_clocked_in = emp_id in active_employees
                    
                    if is_clocked_in:
                        # Show "Active" status instead of clock-in button
                        status_button = MDRaisedButton(
                            text="Active",
                            md_bg_color=[0.1, 0.6, 0.1, 1],  # Darker green
                            text_color=[1, 1, 1, 1],
                            size_hint=(None, None),
                            size=(dp(80), dp(40)),
                            disabled=True
                        )
                        action_box.add_widget(status_button)
                    else:
                        # Show regular clock-in button
                        clock_in_btn = MDRaisedButton(
                            text="Clock In",
                            md_bg_color=[0.2, 0.7, 0.3, 1],  # Green
                            text_color=[1, 1, 1, 1],
                            size_hint=(None, None),
                            size=(dp(80), dp(40)),
                            on_release=lambda x, eid=emp_id, n=name: self.clock_in_and_refresh(eid, n)
                        )
                        action_box.add_widget(clock_in_btn)
                    
                    # Menu button (for more options)
                    menu_btn = MDRaisedButton(
                        text="...",
                        md_bg_color=[0.36, 0.65, 0.82, 1],  # Blue
                        text_color=[1, 1, 1, 1],
                        size_hint=(None, None),
                        size=(dp(40), dp(40)),
                        on_release=lambda x, eid=emp_id, n=name: self.show_employee_menu(eid, n, x)
                    )
                    
                    action_box.add_widget(menu_btn)
                    
                    # Assemble the card
                    employee_card.add_widget(initials_box)
                    employee_card.add_widget(info_box)
                    employee_card.add_widget(action_box)
                    
                    self.employee_list_widget.add_widget(employee_card)
                    
                    # Add a thin divider line if not the last item
                    if i < len(role_groups[role]) - 1:
                        divider = MDBoxLayout(
                            size_hint_y=None,
                            height=1,
                            md_bg_color=[0, 0, 0, 0.1]  # Light gray line
                        )
                        self.employee_list_widget.add_widget(divider)
                
                # Add spacing after each role group
                spacer = MDBoxLayout(size_hint_y=None, height=dp(15))
                self.employee_list_widget.add_widget(spacer)

    def remove_employee(self, emp_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
        self.conn.commit()
        self.show_employees()

    def add_employee_dialog(self, *args):
        layout = MDBoxLayout(orientation='vertical', spacing=5, padding=dp(20), size_hint_y=None)
        layout.height = self.root.height * 0.3

        name_label = MDLabel(text="Enter employee name:", halign="left", theme_text_color="Custom", text_color=[0, 0, 0, 1], size_hint_y=None,  height=dp(20))
        self.name_input = MDTextField(hint_text="Full Name", mode="rectangle")
        self.role_menu_button = MDRaisedButton(
            text="Select Role", 
            on_release=self.open_role_menu,
            md_bg_color=[0.36, 0.65, 0.82, 1],  
            text_color=[1, 1, 1, 1]
        )

        layout.add_widget(name_label)
        layout.add_widget(self.name_input)
        layout.add_widget(self.role_menu_button)

        self.dialog = MDDialog(
            type="custom",
            content_cls=layout,
            buttons=[
                MDRaisedButton(
                    text="Cancel", 
                    on_release=lambda x: self.dialog.dismiss(),
                    md_bg_color=[0.36, 0.65, 0.82, 1], 
                    text_color=[1, 1, 1, 1]
                ),
                MDRaisedButton(
                    text="Save", 
                    on_release=lambda x: self.save_employee(),
                    md_bg_color=[0.36, 0.65, 0.82, 1],  
                    text_color=[1, 1, 1, 1]
                )
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
        """Clock in an employee and show confirmation dialog."""
        clock_in_time = datetime.now()
        
        # Record the time entry in the database
        c = self.conn.cursor()
        c.execute("INSERT INTO timesheets (employee_id, clock_in) VALUES (?, ?)", 
                (emp_id, clock_in_time.isoformat()))
        self.conn.commit()
        
        # Show success message
        clock_in_dialog = MDDialog(
            title="Clock In Successful",
            text=f"{name} has been clocked in at {clock_in_time.strftime('%I:%M %p')}",
            buttons=[
                MDRaisedButton(
                    text="OK", 
                    md_bg_color=[0.36, 0.65, 0.82, 1],
                    text_color=[1, 1, 1, 1],
                    on_release=lambda x: clock_in_dialog.dismiss()
                )
            ]
        )
        clock_in_dialog.open()
            
    def clock_out_specific(self, employee_id, entry_id):
        """Clock out a specific employee's time entry."""
        clock_out_time = datetime.now().isoformat()
        c = self.conn.cursor()
        
        # Get employee name for confirmation
        c.execute("SELECT name FROM employees WHERE id = ?", (employee_id,))
        employee_name = c.fetchone()[0]
        
        # Update the time entry
        c.execute('''UPDATE timesheets SET clock_out=? WHERE id=? AND clock_out IS NULL''', 
                (clock_out_time, entry_id))
        self.conn.commit()
        
        # Show confirmation dialog
        clock_out_dialog = MDDialog(
            title="Clock Out Successful",
            text=f"{employee_name} has been clocked out at {datetime.now().strftime('%I:%M %p')}",
            buttons=[
                MDRaisedButton(
                    text="OK", 
                    md_bg_color=[0.36, 0.65, 0.82, 1],
                    text_color=[1, 1, 1, 1],
                    on_release=lambda x: self.on_clock_out_dialog_close(clock_out_dialog)
                )
            ]
        )
        clock_out_dialog.open()
        
    def on_clock_out_dialog_close(self, dialog):
        """Handle dialog close and refresh time entries."""
        dialog.dismiss()
        # Refresh the time entries display
        self.show_time_entries()

    def clock_in_and_refresh(self, emp_id, name):
        """Clock in an employee and refresh the employee list to update buttons"""
        self.clock_in(emp_id, name)
        self.show_employees() 
        
    def update_timer(self, *args):
        if self.clock_in_time:
            now = datetime.now()
            duration = now - self.clock_in_time
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            formatted = f"{hours:02}:{minutes:02}:{seconds:02}"
            self.clockin_status_label.text = f"{self.employee_name} clocked in | Duration: {formatted}"

    def show_time_entries(self):
        """Display the time entries screen with clock-out functionality for active entries."""
        content = MDBoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Title for the page
        title_label = MDLabel(
            text="Time Entries",
            font_style="H5",
            theme_text_color="Custom",
            text_color=[0.2, 0.2, 0.2, 1],
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(title_label)
        
        # Get time entries from database
        c = self.conn.cursor()
        c.execute('''
            SELECT e.name, e.role, t.clock_in, t.clock_out, t.id, e.id 
            FROM timesheets t 
            JOIN employees e ON e.id = t.employee_id 
            ORDER BY t.clock_in DESC
        ''')
        rows = c.fetchall()
        
        # Create scrollable view
        scroll = ScrollView()
        entries_box = MDBoxLayout(
            orientation='vertical', 
            spacing=5, 
            size_hint_y=None,
            padding=[0, 5, 0, 5]
        )
        entries_box.bind(minimum_height=entries_box.setter('height'))
        
        # Group entries by date
        current_date = None
        for name, role, clock_in, clock_out, entry_id, employee_id in rows:
            if clock_in:
                entry_date = datetime.fromisoformat(clock_in).strftime('%A, %B %d, %Y')
                
                # Add date header if it's a new date
                if entry_date != current_date:
                    current_date = entry_date
                    date_box = BorderedBox(
                        orientation="horizontal",
                        size_hint_y=None,
                        height=dp(40),
                        bg_color=[0.83, 0.94, 0.96, 1],  # Light blue background
                        padding=[10, 0, 10, 0]
                    )
                    date_label = MDLabel(
                        text=entry_date,
                        theme_text_color="Custom",
                        text_color=[0.1, 0.1, 0.1, 1],
                        bold=True
                    )
                    date_box.add_widget(date_label)
                    entries_box.add_widget(date_box)
                
                # Format times
                clock_in_time = datetime.fromisoformat(clock_in).strftime('%I:%M %p')
                
                # Set colors and status based on clock-out status
                if clock_out:
                    clock_out_time = datetime.fromisoformat(clock_out).strftime('%I:%M %p')
                    # Calculate duration
                    duration = datetime.fromisoformat(clock_out) - datetime.fromisoformat(clock_in)
                    hours, remainder = divmod(duration.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    duration_str = f"{hours}h {minutes}m"
                    status = f"Completed shift ({duration_str})"
                    bg_color = [0.95, 0.95, 0.95, 1]  # Light gray for completed shifts
                    entry_height = dp(70)  # Standard height for completed entries
                else:
                    clock_out_time = "Still clocked in"
                    status = "Currently active"
                    bg_color = [0.95, 1, 0.95, 1]  # Light green for active shifts
                    entry_height = dp(100)  # Increased height for active entries with button
                
                # Create entry card with fixed height
                entry_box = BorderedBox(
                    orientation="vertical",
                    size_hint_y=None,
                    height=entry_height,
                    bg_color=bg_color,
                    padding=[15, 5, 15, 5],
                    spacing=2
                )
                
                # Main content container
                content_box = MDBoxLayout(
                    orientation="vertical",
                    size_hint_y=None,
                    height=dp(70),  # Fixed height for content
                    spacing=2
                )
                
                # Row 1: Name and role
                name_role_box = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(25))
                name_label = MDLabel(
                    text=name,
                    theme_text_color="Custom",
                    text_color=[0, 0, 0, 1],
                    bold=True,
                    size_hint_x=0.6
                )
                role_label = MDLabel(
                    text=role,
                    theme_text_color="Custom",
                    text_color=[0.5, 0.5, 0.5, 1],
                    size_hint_x=0.4,
                    halign="right"
                )
                name_role_box.add_widget(name_label)
                name_role_box.add_widget(role_label)
                content_box.add_widget(name_role_box)
                
                # Row 2: Clock times
                times_box = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(25))
                clock_in_label = MDLabel(
                    text=f"In: {clock_in_time}",
                    theme_text_color="Custom",
                    text_color=[0.3, 0.3, 0.3, 1],
                    size_hint_x=0.5
                )
                clock_out_label = MDLabel(
                    text=f"Out: {clock_out_time}",
                    theme_text_color="Custom",
                    text_color=[0.3, 0.3, 0.3, 1],
                    size_hint_x=0.5,
                    halign="right"
                )
                times_box.add_widget(clock_in_label)
                times_box.add_widget(clock_out_label)
                content_box.add_widget(times_box)
                
                # Row 3: Status
                status_box = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(20))
                status_label = MDLabel(
                    text=status,
                    theme_text_color="Custom",
                    text_color=[0.4, 0.4, 0.8, 1] if clock_out else [0.2, 0.7, 0.2, 1],
                    font_style="Caption"
                )
                status_box.add_widget(status_label)
                content_box.add_widget(status_box)
                
                # Add main content to the entry box
                entry_box.add_widget(content_box)
                
                # Add clock-out button for active entries in a separate container
                if not clock_out:
                    button_box = MDBoxLayout(
                        orientation="horizontal", 
                        size_hint_y=None,
                        height=dp(30),
                        padding=[0, 5, 0, 0]
                    )
                    
                    # Push button to the right
                    button_box.add_widget(MDBoxLayout(size_hint_x=0.7))
                    
                    clock_out_btn = MDRaisedButton(
                        text="Clock Out",
                        md_bg_color=[0.36, 0.65, 0.82, 1],
                        text_color=[1, 1, 1, 1],
                        size_hint=(None, None),
                        size=(dp(120), dp(30)),
                        on_release=lambda x, eid=employee_id, tid=entry_id: self.clock_out_specific(eid, tid)
                    )
                    button_box.add_widget(clock_out_btn)
                    entry_box.add_widget(button_box)
                
                entries_box.add_widget(entry_box)
                
                # Add spacing between entries
                spacer = MDBoxLayout(size_hint_y=None, height=dp(5))
                entries_box.add_widget(spacer)
        
        scroll.add_widget(entries_box)
        content.add_widget(scroll)
        
        self.root.get_screen('main').ids.content_area.clear_widgets()
        self.root.get_screen('main').ids.content_area.add_widget(content)

    def show_reports(self):
        content = MDBoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Title
        title_label = MDLabel(
            text="Time Reports",
            font_style="H5",
            theme_text_color="Custom",
            text_color=[0.2, 0.2, 0.2, 1],
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(title_label)
        
        # Create filter section
        filter_box = BorderedBox(
            orientation="vertical",
            size_hint_y=None,
            height=dp(350),  # Increased height for added spacing
            bg_color=[0.97, 0.97, 0.97, 1],
            padding=[20, 20, 20, 20],
            spacing=10
        )
        
        # Filter Options title aligned to the left
        filter_title = MDLabel(
            text="Filter Options",
            theme_text_color="Custom",
            text_color=[0.2, 0.2, 0.2, 1],
            font_style="H6",
            size_hint_y=None,
            height=dp(30),
            halign="left"
        )
        filter_box.add_widget(filter_title)
        
        # Add spacer to create distance between title and form fields (2-3 lines)
        title_spacer = MDBoxLayout(size_hint_y=None, height=dp(30))
        filter_box.add_widget(title_spacer)
        
        # From Date / To Date row
        date_row = MDBoxLayout(
            orientation="horizontal", 
            size_hint_y=None, 
            height=dp(40)
        )
        
        # From Date with minimal spacing
        from_date_label = MDLabel(
            text="From Date:",
            theme_text_color="Custom",
            text_color=[0.3, 0.3, 0.3, 1],
            size_hint_x=None,
            width=dp(80)  # Fixed width for label
        )
        date_row.add_widget(from_date_label)
        
        self.date_from = MDTextField(
            hint_text="YYYY-MM-DD",
            mode="rectangle",
            size_hint_x=0.35
        )
        date_row.add_widget(self.date_from)
        
        # Spacer between from and to date
        date_row.add_widget(MDBoxLayout(size_hint_x=0.05))
        
        # To Date with minimal spacing
        to_date_label = MDLabel(
            text="To Date:",
            theme_text_color="Custom",
            text_color=[0.3, 0.3, 0.3, 1],
            size_hint_x=None,
            width=dp(65)  # Fixed width for label
        )
        date_row.add_widget(to_date_label)
        
        self.date_to = MDTextField(
            hint_text="YYYY-MM-DD",
            mode="rectangle",
            size_hint_x=0.35
        )
        date_row.add_widget(self.date_to)
        
        filter_box.add_widget(date_row)
        
        # Add 1-2 lines of space between date row and quick select
        date_quick_spacer = MDBoxLayout(size_hint_y=None, height=dp(20))
        filter_box.add_widget(date_quick_spacer)
        
        # Quick Select row
        quick_row = MDBoxLayout(
            orientation="horizontal", 
            size_hint_y=None, 
            height=dp(40)
        )
        
        quick_label = MDLabel(
            text="Quick Select:",
            theme_text_color="Custom",
            text_color=[0.3, 0.3, 0.3, 1],
            size_hint_x=None,
            width=dp(100)  # Fixed width for label
        )
        quick_row.add_widget(quick_label)
        
        # Quick select buttons in a row with minimal spacing
        buttons_box = MDBoxLayout(orientation="horizontal", spacing=5)
        
        today_btn = MDRaisedButton(
            text="Today",
            md_bg_color=[0.36, 0.65, 0.82, 1],
            text_color=[1, 1, 1, 1],
            on_release=lambda x: self.set_date_range("today")
        )
        week_btn = MDRaisedButton(
            text="This Week",
            md_bg_color=[0.36, 0.65, 0.82, 1],
            text_color=[1, 1, 1, 1],
            on_release=lambda x: self.set_date_range("week")
        )
        month_btn = MDRaisedButton(
            text="This Month",
            md_bg_color=[0.36, 0.65, 0.82, 1],
            text_color=[1, 1, 1, 1],
            on_release=lambda x: self.set_date_range("month")
        )
        last_month_btn = MDRaisedButton(
            text="Last Month",
            md_bg_color=[0.36, 0.65, 0.82, 1],
            text_color=[1, 1, 1, 1],
            on_release=lambda x: self.set_date_range("last_month")
        )
        
        buttons_box.add_widget(today_btn)
        buttons_box.add_widget(week_btn)
        buttons_box.add_widget(month_btn)
        buttons_box.add_widget(last_month_btn)
        
        quick_row.add_widget(buttons_box)
        filter_box.add_widget(quick_row)
        
        # Add 1-2 lines of space between quick select and employee/roles
        quick_emp_spacer = MDBoxLayout(size_hint_y=None, height=dp(20))
        filter_box.add_widget(quick_emp_spacer)
        
        # Employee/Roles row - adjusted to move roles more to the left
        filter_row = MDBoxLayout(
            orientation="horizontal", 
            size_hint_y=None, 
            height=dp(40)
        )
        
        # Employee with minimal spacing
        employee_label = MDLabel(
            text="Employee:",
            theme_text_color="Custom",
            text_color=[0.3, 0.3, 0.3, 1],
            size_hint_x=None,
            width=dp(80)  # Fixed width for label
        )
        filter_row.add_widget(employee_label)
        
        self.employee_spinner_btn = MDRaisedButton(
            text="All Employees",
            md_bg_color=[0.36, 0.65, 0.82, 1],
            text_color=[1, 1, 1, 1],
            size_hint_x=0.3,  # Reduced to make room for role field
            on_release=lambda x: self.show_employee_menu()
        )
        filter_row.add_widget(self.employee_spinner_btn)
        
        # Moderate spacing between employee and role
        filter_row.add_widget(MDBoxLayout(size_hint_x=0.1))  # Increased spacing
        
        # Role with minimal spacing - moved to the left
        role_label = MDLabel(
            text="Roles:",
            theme_text_color="Custom",
            text_color=[0.3, 0.3, 0.3, 1],
            size_hint_x=None,
            width=dp(50)  # Fixed width for label
        )
        filter_row.add_widget(role_label)
        
        self.role_spinner_btn = MDRaisedButton(
            text="All Roles",
            md_bg_color=[0.36, 0.65, 0.82, 1],
            text_color=[1, 1, 1, 1],
            size_hint_x=0.3,
            on_release=lambda x: self.show_role_menu_for_reports()
        )
        filter_row.add_widget(self.role_spinner_btn)
        
        # Add spacer at the end to prevent roles from being pushed to the right edge
        filter_row.add_widget(MDBoxLayout(size_hint_x=0.15))
        
        filter_box.add_widget(filter_row)
        
        # Add 3 lines of space between employee/roles and buttons
        emp_btn_spacer = MDBoxLayout(size_hint_y=None, height=dp(45))
        filter_box.add_widget(emp_btn_spacer)
        
        # Button row
        button_row = MDBoxLayout(
            orientation="horizontal", 
            size_hint_y=None, 
            height=dp(40),
            spacing=20
        )
        
        # Light blue buttons with black text
        generate_btn = MDRaisedButton(
            text="Generate Report",
            md_bg_color=[0.83, 0.94, 0.96, 1],  # Lighter blue color
            text_color=[0, 0, 0, 1],  # Black text
            on_release=lambda x: self.generate_report()
        )
        
        export_btn = MDRaisedButton(
            text="Export to CSV",
            md_bg_color=[0.83, 0.94, 0.96, 1],  # Lighter blue color
            text_color=[0, 0, 0, 1],  # Black text
            on_release=lambda x: self.export_to_csv()
        )
        
        button_row.add_widget(generate_btn)
        button_row.add_widget(export_btn)
        button_row.add_widget(MDBoxLayout())  # Flexible spacer to push buttons left
        
        filter_box.add_widget(button_row)
        
        content.add_widget(filter_box)
        
        # Results section
        self.report_results = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=5,
            padding=[0, 10, 0, 10]
        )
        self.report_results.bind(minimum_height=self.report_results.setter('height'))
        
        # Initially show summary statistics
        self.show_report_summary()
        
        report_scroll = ScrollView()
        report_scroll.add_widget(self.report_results)
        content.add_widget(report_scroll)
        
        self.root.get_screen('main').ids.content_area.clear_widgets()
        self.root.get_screen('main').ids.content_area.add_widget(content)

    def set_date_range(self, period):
        today = datetime.now()
        if period == "today":
            self.date_from.text = today.strftime("%Y-%m-%d")
            self.date_to.text = today.strftime("%Y-%m-%d")
        elif period == "week":
            start_of_week = today - timedelta(days=today.weekday())
            self.date_from.text = start_of_week.strftime("%Y-%m-%d")
            self.date_to.text = today.strftime("%Y-%m-%d")
        elif period == "month":
            start_of_month = today.replace(day=1)
            self.date_from.text = start_of_month.strftime("%Y-%m-%d")
            self.date_to.text = today.strftime("%Y-%m-%d")
        elif period == "last_month":
            # First day of current month
            first_day_current = today.replace(day=1)
            # Last day of previous month
            last_day_previous = first_day_current - timedelta(days=1)
            # First day of previous month
            first_day_previous = last_day_previous.replace(day=1)
            
            self.date_from.text = first_day_previous.strftime("%Y-%m-%d")
            self.date_to.text = last_day_previous.strftime("%Y-%m-%d")

    def show_employee_menu(self, emp_id, name, instance):
        menu_items = [
            {
                "text": "Remove Employee",
                "viewclass": "OneLineListItem",
                "on_release": lambda: self.select_employee_action("remove", emp_id, name)
            }
        ]
        
        self.emp_menu = MDDropdownMenu(
            caller=instance,
            items=menu_items,
            width_mult=3
        )
        self.emp_menu.open()

    def select_employee_for_report(self, emp_id, name):
        self.selected_employee_id = emp_id
        self.employee_spinner_btn.text = name
        if hasattr(self, 'employee_menu'):
            self.employee_menu.dismiss()

    def show_role_menu_for_reports(self):
        menu_items = [
            {
                "text": "All Roles",
                "viewclass": "OneLineListItem",
                "on_release": lambda: self.select_role_for_report("All Roles")
            }
        ]
        
        for role in self.employee_roles:
            menu_items.append(
                {
                    "text": role,
                    "viewclass": "OneLineListItem",
                    "on_release": lambda r=role: self.select_role_for_report(r)
                }
            )
        
        self.role_menu = MDDropdownMenu(
            caller=self.role_spinner_btn,
            items=menu_items,
            width_mult=4
        )
        self.role_menu.open()

    def select_role_for_report(self, role):
        self.selected_role = role if role != "All Roles" else None
        self.role_spinner_btn.text = role
        if hasattr(self, 'role_menu'):
            self.role_menu.dismiss()

    def generate_report(self):
        # Clear previous results
        self.report_results.clear_widgets()
        
        # Get filter values
        from_date = self.date_from.text.strip()
        to_date = self.date_to.text.strip()
        
        # Validate dates
        if from_date and to_date:
            try:
                datetime.strptime(from_date, "%Y-%m-%d")
                datetime.strptime(to_date, "%Y-%m-%d")
            except ValueError:
                self.show_error_message("Please enter valid dates in YYYY-MM-DD format")
                return
        
        # Build query
        query = '''
            SELECT e.name, e.role, t.clock_in, t.clock_out, t.id 
            FROM timesheets t 
            JOIN employees e ON e.id = t.employee_id 
            WHERE 1=1
        '''
        params = []
        
        if from_date:
            query += " AND DATE(t.clock_in) >= ?"
            params.append(from_date)
        
        if to_date:
            query += " AND DATE(t.clock_in) <= ?"
            params.append(to_date)
        
        if hasattr(self, 'selected_employee_id') and self.selected_employee_id is not None:
            query += " AND e.id = ?"
            params.append(self.selected_employee_id)
        
        if hasattr(self, 'selected_role') and self.selected_role is not None:
            query += " AND e.role = ?"
            params.append(self.selected_role)
        
        query += " ORDER BY t.clock_in DESC"
        
        # Execute query
        c = self.conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        
        # Display results
        if not rows:
            no_results = MDLabel(
                text="No time entries found for the selected criteria",
                theme_text_color="Custom",
                text_color=[0.5, 0.5, 0.5, 1],
                halign="center"
            )
            self.report_results.add_widget(no_results)
            return
        
        # Add summary stats
        self.add_report_summary(rows)
        
        # Add detail table header
        header_box = BorderedBox(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(40),
            bg_color=[0.83, 0.94, 0.96, 1]
        )
        
        headers = ["Employee", "Role", "Date", "Time In", "Time Out", "Duration"]
        header_widths = [0.25, 0.15, 0.20, 0.15, 0.15, 0.10]
        
        for header, width in zip(headers, header_widths):
            header_label = MDLabel(
                text=header,
                theme_text_color="Custom",
                text_color=[0, 0, 0, 1],
                size_hint_x=width,
                bold=True,
                halign="center"
            )
            header_box.add_widget(header_label)
        
        self.report_results.add_widget(header_box)
        
        # Add rows
        for i, (name, role, clock_in, clock_out, _) in enumerate(rows):
            # Format dates
            if clock_in:
                ci_dt = datetime.fromisoformat(clock_in)
                date_str = ci_dt.strftime('%Y-%m-%d')
                time_in_str = ci_dt.strftime('%I:%M %p')
            else:
                date_str = "---"
                time_in_str = "---"
            
            if clock_out:
                co_dt = datetime.fromisoformat(clock_out)
                time_out_str = co_dt.strftime('%I:%M %p')
                
                # Calculate duration
                duration = co_dt - ci_dt
                hours, remainder = divmod(duration.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                duration_str = f"{hours}h {minutes}m"
            else:
                time_out_str = "Active"
                duration_str = "---"
            
            # Alternate row colors
            bg_color = [0.95, 0.95, 0.95, 1] if i % 2 == 0 else [1, 1, 1, 1]
            
            row_box = BorderedBox(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(30),
                bg_color=bg_color
            )
            
            row_data = [name, role, date_str, time_in_str, time_out_str, duration_str]
            
            for data, width in zip(row_data, header_widths):
                cell_label = MDLabel(
                    text=data,
                    theme_text_color="Custom",
                    text_color=[0.2, 0.2, 0.2, 1],
                    size_hint_x=width,
                    halign="center"
                )
                row_box.add_widget(cell_label)
            
            self.report_results.add_widget(row_box)

    def add_report_summary(self, rows):
        # Calculate summary statistics
        total_shifts = len(rows)
        total_hours = 0
        completed_shifts = 0
        
        # Process data for summary
        employee_hours = {}
        role_hours = {}
        date_hours = {}
        
        for name, role, clock_in, clock_out, _ in rows:
            if clock_in and clock_out:
                duration = datetime.fromisoformat(clock_out) - datetime.fromisoformat(clock_in)
                hours = duration.total_seconds() / 3600
                total_hours += hours
                completed_shifts += 1
                
                # By employee
                if name in employee_hours:
                    employee_hours[name] += hours
                else:
                    employee_hours[name] = hours
                    
                # By role
                if role in role_hours:
                    role_hours[role] += hours
                else:
                    role_hours[role] = hours
                    
                # By date
                date_str = datetime.fromisoformat(clock_in).strftime('%Y-%m-%d')
                if date_str in date_hours:
                    date_hours[date_str] += hours
                else:
                    date_hours[date_str] = hours
        
        # Create summary box
        summary_box = BorderedBox(
            orientation="vertical",
            size_hint_y=None,
            height=dp(150),
            bg_color=[0.97, 0.97, 0.97, 1],
            padding=[15, 10, 15, 10],
            spacing=5
        )
        
        summary_title = MDLabel(
            text="Summary Statistics",
            theme_text_color="Custom",
            text_color=[0.2, 0.2, 0.2, 1],
            font_style="H6",
            size_hint_y=None,
            height=dp(30)
        )
        summary_box.add_widget(summary_title)
        
        # Basic statistics
        stats_box = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30))
        
        total_shifts_label = MDLabel(
            text=f"Total Shifts: {total_shifts}",
            theme_text_color="Custom",
            text_color=[0.2, 0.2, 0.2, 1],
            size_hint_x=0.33
        )
        completed_shifts_label = MDLabel(
            text=f"Completed Shifts: {completed_shifts}",
            theme_text_color="Custom",
            text_color=[0.2, 0.2, 0.2, 1],
            size_hint_x=0.33
        )
        total_hours_label = MDLabel(
            text=f"Total Hours: {total_hours:.2f}",
            theme_text_color="Custom",
            text_color=[0.2, 0.2, 0.2, 1],
            size_hint_x=0.33
        )
        
        stats_box.add_widget(total_shifts_label)
        stats_box.add_widget(completed_shifts_label)
        stats_box.add_widget(total_hours_label)
        summary_box.add_widget(stats_box)
        
        # Top contributors
        if employee_hours:
            top_employees = sorted(employee_hours.items(), key=lambda x: x[1], reverse=True)[:3]
            top_emp_box = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30))
            
            top_emp_title = MDLabel(
                text="Top Contributors:",
                theme_text_color="Custom",
                text_color=[0.2, 0.2, 0.2, 1],
                bold=True,
                size_hint_x=0.3
            )
            top_emp_box.add_widget(top_emp_title)
            
            top_emp_data = MDLabel(
                text=", ".join([f"{name} ({hours:.1f}h)" for name, hours in top_employees]),
                theme_text_color="Custom",
                text_color=[0.2, 0.2, 0.2, 1],
                size_hint_x=0.7
            )
            top_emp_box.add_widget(top_emp_data)
            summary_box.add_widget(top_emp_box)
        
        # Hours by role
        if role_hours:
            role_box = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30))
            
            role_title = MDLabel(
                text="Hours by Role:",
                theme_text_color="Custom",
                text_color=[0.2, 0.2, 0.2, 1],
                bold=True,
                size_hint_x=0.3
            )
            role_box.add_widget(role_title)
            
            role_data = MDLabel(
                text=", ".join([f"{role} ({hours:.1f}h)" for role, hours in sorted(role_hours.items(), key=lambda x: x[1], reverse=True)]),
                theme_text_color="Custom",
                text_color=[0.2, 0.2, 0.2, 1],
                size_hint_x=0.7
            )
            role_box.add_widget(role_data)
            summary_box.add_widget(role_box)
        
        self.report_results.add_widget(summary_box)
        
        # Add spacing
        spacer = MDBoxLayout(size_hint_y=None, height=dp(10))
        self.report_results.add_widget(spacer)

    def show_report_summary(self):
        self.report_results.clear_widgets()
        
        initial_box = BorderedBox(
            orientation="vertical",
            size_hint_y=None,
            height=dp(100),
            bg_color=[0.97, 0.97, 0.97, 1],
            padding=[15, 10, 15, 10]
        )
        
        welcome_label = MDLabel(
            text="Welcome to the Reports Section",
            theme_text_color="Custom",
            text_color=[0.2, 0.2, 0.2, 1],
            font_style="H6"
        )
        initial_box.add_widget(welcome_label)
        
        instr_label = MDLabel(
            text="Use the filters above to generate custom time reports.\nYou can filter by date range, employee, or role.",
            theme_text_color="Custom",
            text_color=[0.4, 0.4, 0.4, 1],
            font_style="Body1"
        )
        initial_box.add_widget(instr_label)
        
        self.report_results.add_widget(initial_box)

    def show_error_message(self, message):
        dialog = MDDialog(
            title="Error",
            text=message,
            buttons=[
                MDRaisedButton(
                    text="OK", 
                    md_bg_color=[0.36, 0.65, 0.82, 1],
                    text_color=[1, 1, 1, 1],
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()
        
    def export_to_csv(self):
        # Get filter values
        from_date = self.date_from.text.strip()
        to_date = self.date_to.text.strip()
        
        # Build query
        query = '''
            SELECT e.name, e.role, t.clock_in, t.clock_out 
            FROM timesheets t 
            JOIN employees e ON e.id = t.employee_id 
            WHERE 1=1
        '''
        params = []
        
        if from_date:
            query += " AND DATE(t.clock_in) >= ?"
            params.append(from_date)
        
        if to_date:
            query += " AND DATE(t.clock_in) <= ?"
            params.append(to_date)
        
        if hasattr(self, 'selected_employee_id') and self.selected_employee_id is not None:
            query += " AND e.id = ?"
            params.append(self.selected_employee_id)
        
        if hasattr(self, 'selected_role') and self.selected_role is not None:
            query += " AND e.role = ?"
            params.append(self.selected_role)
        
        query += " ORDER BY t.clock_in DESC"
        
        # Execute query
        c = self.conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        
        if not rows:
            self.show_error_message("No data to export")
            return
        
        try:
            # Generate a filename with timestamp
            import os
            from datetime import datetime
            import csv
            
            # Create a desktop path for the CSV file
            home_dir = os.path.expanduser("~")
            desktop_dir = os.path.join(home_dir, "Desktop")
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create filename with filters included
            filename_parts = ["volunteer_report"]
            
            if from_date:
                filename_parts.append(f"from_{from_date}")
            if to_date:
                filename_parts.append(f"to_{to_date}")
            if hasattr(self, 'selected_employee_id') and self.selected_employee_id is not None:
                employee_name = self.employee_spinner_btn.text.replace(" ", "_")
                filename_parts.append(employee_name)
            if hasattr(self, 'selected_role') and self.selected_role is not None:
                role_name = self.role_spinner_btn.text.replace(" ", "_")
                filename_parts.append(role_name)
                
            filename_parts.append(date_str)
            filename = "_".join(filename_parts) + ".csv"
            
            # Full path for the file
            file_path = os.path.join(desktop_dir, filename)
            
            # Create CSV file
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(['Name', 'Role', 'Clock In', 'Clock Out', 'Duration (Hours)'])
                
                # Write data
                for name, role, clock_in, clock_out in rows:
                    # Format times
                    if clock_in:
                        clock_in_fmt = datetime.fromisoformat(clock_in).strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        clock_in_fmt = ""
                    
                    if clock_out:
                        clock_out_fmt = datetime.fromisoformat(clock_out).strftime('%Y-%m-%d %H:%M:%S')
                        # Calculate duration
                        duration = (datetime.fromisoformat(clock_out) - 
                                datetime.fromisoformat(clock_in)).total_seconds() / 3600
                        duration_fmt = f"{duration:.2f}"
                    else:
                        clock_out_fmt = ""
                        duration_fmt = ""
                    
                    writer.writerow([name, role, clock_in_fmt, clock_out_fmt, duration_fmt])
            
            # Show success message
            success_dialog = MDDialog(
                title="Export Successful",
                text=f"Report has been exported to your Desktop:\n{filename}",
                buttons=[
                    MDRaisedButton(
                        text="OK", 
                        md_bg_color=[0.83, 0.94, 0.96, 1],
                        text_color=[0, 0, 0, 1],
                        on_release=lambda x: success_dialog.dismiss()
                    )
                ]
            )
            success_dialog.open()
            
        except Exception as e:
            self.show_error_message(f"Error exporting data: {str(e)}")

if __name__ == '__main__':
    VolunteerApp().run()