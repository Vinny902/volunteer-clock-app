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
            height: dp(45)
            padding: dp(10)
            spacing: dp(15)
            md_bg_color: [0.36, 0.65, 0.82, 1]

            MDRaisedButton:
                text: "Home"
                md_bg_color: [0.36, 0.65, 0.82, 1]
                text_color: [1, 1, 1, 1]
                on_release: app.show_home()

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
            height: dp(25)
            padding: dp(10), 0
            spacing: dp(10)
            md_bg_color: [0.83, 0.94, 0.96, 1]

            Image:
                source: "logo.jpg"  
                size_hint: None, None
                size: dp(35), dp(35)
                allow_stretch: True
                
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
            height: dp(25)
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
        
        # Load roles from the database
        self.load_roles_from_db()
        
        self.root = Builder.load_string(KV)

        self.realtime_label = self.root.get_screen('main').ids.realtime_clock
        self.clockin_status_label = self.root.get_screen('main').ids.clockin_status
        self.clockin_status_bar = self.root.get_screen('main').ids.clockin_status_bar

        Clock.schedule_interval(self.update_realtime_clock, 1)
        self.show_home()
        return self.root

    def create_tables(self):
        c = self.conn.cursor()
        
        # Create tables if they don't exist
        c.execute('''CREATE TABLE IF NOT EXISTS employees (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        first_name TEXT NOT NULL,
                        last_name TEXT NOT NULL,
                        role TEXT NOT NULL,
                        price_per_hour REAL DEFAULT 0
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS timesheets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id INTEGER,
                        clock_in TEXT,
                        clock_out TEXT,
                        FOREIGN KEY(employee_id) REFERENCES employees(id)
                    )''')
        
        # Create a table for roles
        c.execute('''CREATE TABLE IF NOT EXISTS roles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE
                    )''')
        
        # Check if price_per_hour column exists, if not, add it
        c.execute("PRAGMA table_info(employees)")
        columns = c.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'price_per_hour' not in column_names:
            c.execute("ALTER TABLE employees ADD COLUMN price_per_hour REAL DEFAULT 0")
        
        # Insert default roles if roles table is empty
        c.execute("SELECT COUNT(*) FROM roles")
        if c.fetchone()[0] == 0:
            for role in self.employee_roles:
                c.execute("INSERT INTO roles (name) VALUES (?)", (role,))
        
        self.conn.commit()

    def update_realtime_clock(self, *args):
        now = datetime.now().strftime("%I:%M:%S %p | %A, %B %d, %Y")
        self.realtime_label.text = now
        self.update_timer()

    def show_home(self):
        """Display a welcoming home screen with summary information and app description."""
        # Create a scroll view to handle content when window is resized
        scroll_view = ScrollView()
        
        # Main content box that will be scrollable
        content = MDBoxLayout(
            orientation='vertical', 
            spacing=10, 
            padding=[20, 0, 20, 0],
            size_hint_y=None
        )
        content.bind(minimum_height=content.setter('height'))
        
        # Welcome banner with clinic name and volunteer management - increased height
        welcome_box = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(500),  
            padding=[15, 30, 15, 15],  
            md_bg_color=[0.36, 0.65, 0.82, 0.15], 
            radius=[10, 10, 10, 10] 
        )
        
        # Add spacer at the top to push content down
        welcome_box.add_widget(MDBoxLayout(size_hint_y=None, height=dp(50)))
        
        welcome_title = MDLabel(
            text="Welcome to Good Samaritan Clinic",
            font_style="H4",  # Larger font style
            theme_text_color="Custom",
            text_color=[0.2, 0.2, 0.2, 1],
            halign="center",
            valign="middle",  # Center vertically
            size_hint_y=None,
            height=dp(100)  
        )
        
        welcome_subtitle = MDLabel(
            text="Volunteer Time Management System",
            font_style="H5",  # Larger font style
            theme_text_color="Custom",
            text_color=[0.3, 0.3, 0.3, 1],
            halign="center",
            valign="middle",  # Center vertically
            size_hint_y=None,
            height=dp(80)  # Using your increased height but slightly reduced
        )
        
        welcome_desc = MDLabel(
            text="Track volunteer hours, manage staff, and generate reports",
            font_style="H6",  # Larger font style
            theme_text_color="Custom",
            text_color=[0.4, 0.4, 0.4, 1],
            halign="center",
            valign="middle",  # Center vertically
            size_hint_y=None,
            height=dp(80)  # Using your increased height but slightly reduced
        )
        
        # Add another spacer at the bottom to push content up
        bottom_spacer = MDBoxLayout(size_hint_y=None, height=dp(100))
        
        welcome_box.add_widget(welcome_title)
        welcome_box.add_widget(welcome_subtitle)
        welcome_box.add_widget(welcome_desc)
        welcome_box.add_widget(bottom_spacer)
        content.add_widget(welcome_box)
        
        # Stats and quick access row
        stats_container = MDGridLayout(
            cols=2,  # 2 columns by default for larger screens
            size_hint_y=None,
            height=dp(350),  # Increased height to accommodate title boxes
            spacing=15,
            padding=[0, 10, 0, 0]
        )
        
        # Set columns based on width
        stats_container.bind(
            width=lambda *x: setattr(
                stats_container, 'cols', 1 if stats_container.width < dp(600) else 2
            )
        )
        
        # Left Column - Today's Activity
        left_column = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(350),
            spacing=5  # Reduced spacing between elements
        )
        
        # Today's Activity title box
        activity_title_box = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(50),
            md_bg_color=[0.95, 0.95, 0.95, 1],
            radius=[10, 10, 10, 10]
        )
        
        activity_title = MDLabel(
            text="Today's Activity",
            font_style="H6",
            theme_text_color="Custom",
            text_color=[0.2, 0.2, 0.2, 1],
            halign="center",
            size_hint_y=None,
            height=dp(50)
        )
        
        activity_title_box.add_widget(activity_title)
        left_column.add_widget(activity_title_box)
        
        # Stats box
        stats_box = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(290),
            padding=[15, 0, 15, 0],  # Removed vertical padding
            md_bg_color=[0.95, 0.95, 0.95, 1],
            radius=[10, 10, 10, 10]
        )
        
        # Fetch today's stats from the database
        c = self.conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Get active volunteers
        c.execute('''
            SELECT COUNT(DISTINCT employee_id) FROM timesheets 
            WHERE DATE(clock_in) = ? AND clock_out IS NULL
        ''', (today,))
        active_count = c.fetchone()[0]
        
        # Get completed shifts today
        c.execute('''
            SELECT COUNT(*) FROM timesheets 
            WHERE DATE(clock_in) = ? AND clock_out IS NOT NULL
        ''', (today,))
        completed_count = c.fetchone()[0]
        
        # Get total volunteers who worked today
        c.execute('''
            SELECT COUNT(DISTINCT employee_id) FROM timesheets 
            WHERE DATE(clock_in) = ?
        ''', (today,))
        total_volunteers = c.fetchone()[0]
        
        # NO top spacer in stats box
        
        # Display the stats with reduced heights and less spacing between them
        active_label = MDLabel(
            text=f"Active Volunteers: {active_count}",
            font_style="H6",
            theme_text_color="Custom",
            text_color=[0.2, 0.7, 0.2, 1],
            halign="center",
            size_hint_y=None,
            height=dp(70)  # Reduced from 80
        )
        completed_label = MDLabel(
            text=f"Completed Shifts: {completed_count}",
            font_style="H6",
            theme_text_color="Custom",
            text_color=[0.4, 0.4, 0.8, 1],
            halign="center",
            size_hint_y=None,
            height=dp(70)  # Reduced from 80
        )
        total_label = MDLabel(
            text=f"Total Volunteers Today: {total_volunteers}",
            font_style="H6",
            theme_text_color="Custom",
            text_color=[0.3, 0.3, 0.3, 1],
            halign="center",
            size_hint_y=None,
            height=dp(70)  # Reduced from 80
        )
        
        # Add minimal spacing for vertical distribution
        stats_box.add_widget(MDBoxLayout(size_hint_y=None, height=dp(15)))  # Small top space
        stats_box.add_widget(active_label)
        stats_box.add_widget(completed_label)
        stats_box.add_widget(total_label)
        stats_box.add_widget(MDBoxLayout(size_hint_y=None, height=dp(35)))  # Adjusted bottom space
        
        left_column.add_widget(stats_box)
        
        # Right section - Quick Access
        right_column = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(350),
            spacing=5  # Reduced spacing between elements
        )
        
        # Quick Access title box
        quick_access_title_box = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(50),
            md_bg_color=[0.95, 0.95, 0.95, 1],
            radius=[10, 10, 10, 10]
        )
        
        quick_access_title = MDLabel(
            text="Quick Access",
            font_style="H6",
            theme_text_color="Custom",
            text_color=[0.2, 0.2, 0.2, 1],
            halign="center",
            size_hint_y=None,
            height=dp(50)
        )
        
        quick_access_title_box.add_widget(quick_access_title)
        right_column.add_widget(quick_access_title_box)
        
        # Buttons container
        buttons_box = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(290),
            spacing=5,  # Reduced spacing
            padding=[15, 0, 15, 0],  # Removed vertical padding
            md_bg_color=[0.95, 0.95, 0.95, 1],
            radius=[10, 10, 10, 10]
        )
        
        # No top spacer - buttons will start at the top
        buttons_box.add_widget(MDBoxLayout(size_hint_y=None, height=dp(15)))  # Minimal top space
        
        # Add employee button with fixed width
        add_emp_btn = MDRaisedButton(
            text="Add New Employee",
            md_bg_color=[0.36, 0.65, 0.82, 1],
            text_color=[1, 1, 1, 1],
            size_hint=(None, None),
            size=(dp(180), dp(45)),
            pos_hint={"center_x": 0.5}  # Center horizontally
        )
        add_emp_btn.bind(on_release=lambda x: self.add_employee_dialog())
        buttons_box.add_widget(add_emp_btn)
        
        # Add spacing between buttons
        buttons_box.add_widget(MDBoxLayout(size_hint_y=None, height=dp(30)))
        
        # View active shifts button
        view_active_btn = MDRaisedButton(
            text="View Active Shifts",
            md_bg_color=[0.2, 0.7, 0.3, 1],  # Green for active
            text_color=[1, 1, 1, 1],
            size_hint=(None, None),
            size=(dp(180), dp(45)),
            pos_hint={"center_x": 0.5}  # Center horizontally
        )
        view_active_btn.bind(on_release=lambda x: self.show_time_entries())
        buttons_box.add_widget(view_active_btn)
        
        # Add spacing between buttons
        buttons_box.add_widget(MDBoxLayout(size_hint_y=None, height=dp(30)))
        
        # Generate report button
        report_btn = MDRaisedButton(
            text="Generate Today's Report",
            md_bg_color=[0.83, 0.94, 0.96, 1],  # Light blue
            text_color=[0, 0, 0, 1],
            size_hint=(None, None),
            size=(dp(180), dp(45)),
            pos_hint={"center_x": 0.5}  # Center horizontally
        )
        report_btn.bind(on_release=lambda x: self.generate_todays_report())
        buttons_box.add_widget(report_btn)
        
        # Add bottom space to balance
        buttons_box.add_widget(MDBoxLayout(size_hint_y=None, height=dp(45)))
        
        right_column.add_widget(buttons_box)
        
        # Add the two columns to the container
        stats_container.add_widget(left_column)
        stats_container.add_widget(right_column)
        content.add_widget(stats_container)
        
        # Footer with app info
        footer = MDLabel(
            text="© 2025 Good Samaritan Clinic - Volunteer Management App",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=[0.5, 0.5, 0.5, 1],
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        content.add_widget(footer)
        content.add_widget(MDBoxLayout(size_hint_y=None, height=dp(20)))  # Bottom padding
        
        # Add content to scroll view
        scroll_view.add_widget(content)
        
        # Clear and add to screen
        self.root.get_screen('main').ids.content_area.clear_widgets()
        self.root.get_screen('main').ids.content_area.add_widget(scroll_view)
    
    def add_new_role_dialog(self, *args):
        # Temporarily dismiss the main dialog
        self.dialog.dismiss()
        
        # Create new dialog for adding a role
        role_layout = MDBoxLayout(orientation='vertical', spacing=15, padding=dp(20), size_hint_y=None, height=dp(120))
        
        role_label = MDLabel(
            text="Enter new role name:",
            halign="left",
            theme_text_color="Custom",
            text_color=[0, 0, 0, 1],
            size_hint_y=None,
            height=dp(20)
        )
        
        self.new_role_input = MDTextField(
            hint_text="New Role",
            mode="rectangle"
        )
        
        role_layout.add_widget(role_label)
        role_layout.add_widget(self.new_role_input)
        
        self.role_dialog = MDDialog(
            title="Add New Role",
            type="custom",
            content_cls=role_layout,
            buttons=[
                MDRaisedButton(
                    text="Cancel", 
                    on_release=lambda x: self.cancel_new_role(),
                    md_bg_color=[0.36, 0.65, 0.82, 1], 
                    text_color=[1, 1, 1, 1]
                ),
                MDRaisedButton(
                    text="Add Role", 
                    on_release=lambda x: self.confirm_new_role(),
                    md_bg_color=[0.2, 0.7, 0.3, 1],  # Green
                    text_color=[1, 1, 1, 1]
                )
            ]
        )
        self.role_dialog.open()

    def cancel_new_role(self):
        # Close the role dialog and reopen the main employee dialog
        self.role_dialog.dismiss()
        self.add_employee_dialog()

    def confirm_new_role(self):
        new_role = self.new_role_input.text.strip()
        
        if not new_role:
            error_dialog = MDDialog(
                title="Error",
                text="Please enter a role name.",
                buttons=[
                    MDRaisedButton(text="OK", on_release=lambda x: error_dialog.dismiss())
                ]
            )
            error_dialog.open()
            return
        
        # Add the new role to the list if it's not already there
        if new_role not in self.employee_roles:
            self.employee_roles.append(new_role)
            # Sort roles alphabetically
            self.employee_roles.sort()
        
        # Select this role for the employee
        self.role_selected = new_role
        
        # Close the role dialog
        self.role_dialog.dismiss()
        
        # Reopen the employee dialog with the new role selected
        self.add_employee_dialog()
        self.role_menu_button.text = new_role
    
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
        
    def select_employee_action(self, action, emp_id, name):
        """Handle employee actions from the menu."""
        if action == "remove":
            # Prompt for PIN before confirming deletion
            self.prompt_pin(lambda: self.show_remove_confirmation(emp_id, name))
            
            # Dismiss the employee menu if it's open
            if hasattr(self, 'emp_menu'):
                self.emp_menu.dismiss()
    
    def show_remove_confirmation(self, emp_id, name):
        """Show confirmation dialog after PIN verification."""
        confirm_dialog = MDDialog(
            title="Confirm Removal",
            text=f"Are you sure you want to remove {name}?",
            buttons=[
                MDRaisedButton(
                    text="Cancel", 
                    md_bg_color=[0.36, 0.65, 0.82, 1],
                    text_color=[1, 1, 1, 1],
                    on_release=lambda x: confirm_dialog.dismiss()
                ),
                MDRaisedButton(
                    text="Remove", 
                    md_bg_color=[0.8, 0.2, 0.2, 1],  # Red color for delete
                    text_color=[1, 1, 1, 1],
                    on_release=lambda x: self.confirm_remove_employee(confirm_dialog, emp_id)
                )
            ]
        )
        confirm_dialog.open()

    def confirm_remove_employee(self, dialog, emp_id):
        """Confirm and execute employee removal."""
        dialog.dismiss()
        self.remove_employee(emp_id) 
    
    def load_roles_from_db(self):
        """Load roles from the database"""
        c = self.conn.cursor()
        c.execute("SELECT name FROM roles ORDER BY name")
        roles = c.fetchall()
        self.employee_roles = [role[0] for role in roles]
          
    def load_employees(self, filter_text=""):
        self.employee_list_widget.clear_widgets()
        c = self.conn.cursor()
        
        # First, get all active clock-ins to check which employees are currently clocked in
        c.execute('''
            SELECT employee_id FROM timesheets 
            WHERE clock_out IS NULL
        ''')
        active_employees = {row[0] for row in c.fetchall()}
        
        # Fetch all employees with separated first and last names
        c.execute("SELECT id, first_name, last_name, role FROM employees ORDER BY role, last_name, first_name")
        employees = c.fetchall()
        
        # Create a dictionary to group employees by role
        role_groups = {}
        
        # Filter and group employees
        for emp_id, first_name, last_name, role in employees:
            # Combine names for display
            full_name = f"{first_name} {last_name}".strip()
            
            # Apply filter on the combined name
            if filter_text and filter_text not in full_name.lower():
                continue
                    
            if role not in role_groups:
                role_groups[role] = []
            
            role_groups[role].append((emp_id, full_name))
        
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
                    
                    # Change background for active employees
                    is_clocked_in = emp_id in active_employees
                    if is_clocked_in:
                        employee_card.md_bg_color = [0.9, 1, 0.9, 1]  # Light green background
                    
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
                    if is_clocked_in:
                        # Get the timesheet entry id for this employee to clock them out
                        c.execute('''
                            SELECT id FROM timesheets 
                            WHERE employee_id = ? AND clock_out IS NULL
                            ORDER BY clock_in DESC LIMIT 1
                        ''', (emp_id,))
                        timesheet_entry = c.fetchone()
                        
                        if timesheet_entry:
                            entry_id = timesheet_entry[0]
                            # Show Clock Out button instead of disabled Active status
                            clock_out_btn = MDRaisedButton(
                                text="Clock Out",
                                md_bg_color=[0.1, 0.6, 0.1, 1],  # Darker green
                                text_color=[1, 1, 1, 1],
                                size_hint=(None, None),
                                size=(dp(80), dp(40)),
                                on_release=lambda x, eid=emp_id, tid=entry_id: self.clock_out_and_refresh(eid, tid)
                            )
                            action_box.add_widget(clock_out_btn)
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
        layout.height = self.root.height * 0.55  # Increased height to accommodate all fields
        
        # First Name field
        first_name_label = MDLabel(
            text="First Name:*", 
            halign="left", 
            theme_text_color="Custom", 
            text_color=[0, 0, 0, 1], 
            size_hint_y=None, 
            height=dp(20)
        )
        self.first_name_input = MDTextField(hint_text="First Name", mode="rectangle")
        
        # Last Name field
        last_name_label = MDLabel(
            text="Last Name:*", 
            halign="left", 
            theme_text_color="Custom", 
            text_color=[0, 0, 0, 1], 
            size_hint_y=None, 
            height=dp(20)
        )
        self.last_name_input = MDTextField(hint_text="Last Name", mode="rectangle")
        
        # Price/hour field
        price_label = MDLabel(
            text="Price per hour ($):*", 
            halign="left", 
            theme_text_color="Custom", 
            text_color=[0, 0, 0, 1], 
            size_hint_y=None, 
            height=dp(20)
        )
        self.price_input = MDTextField(hint_text="0.00", mode="rectangle", input_filter="float")
        
        # Role section with existing roles dropdown
        role_label = MDLabel(
            text="Role:*", 
            halign="left", 
            theme_text_color="Custom", 
            text_color=[0, 0, 0, 1], 
            size_hint_y=None, 
            height=dp(20)
        )
        
        # Create role selection box
        self.role_selected = None
        role_dropdown_box = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(50),
            spacing=5
        )
        
        self.role_menu_button = MDRaisedButton(
            text="Select Role", 
            on_release=self.open_role_menu,
            md_bg_color=[0.36, 0.65, 0.82, 1],  
            text_color=[1, 1, 1, 1],
            size_hint_x=1
        )
        role_dropdown_box.add_widget(self.role_menu_button)
        
        # New role section
        new_role_label = MDLabel(
            text="Or add a new role:", 
            halign="left", 
            theme_text_color="Custom", 
            text_color=[0, 0, 0, 1], 
            size_hint_y=None, 
            height=dp(20)
        )
        
        new_role_box = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(50),
            spacing=10
        )
        
        self.new_role_input = MDTextField(
            hint_text="New Role Name",
            mode="rectangle",
            size_hint_x=0.7
        )
        
        add_role_btn = MDRaisedButton(
            text="Add", 
            on_release=lambda x: self.add_new_role_inline(),
            md_bg_color=[0.36, 0.65, 0.82, 1],  
            text_color=[1, 1, 1, 1],
            size_hint_x=0.3
        )
        
        new_role_box.add_widget(self.new_role_input)
        new_role_box.add_widget(add_role_btn)
        
        # Required fields note
        required_note = MDLabel(
            text="* All fields are required", 
            halign="left", 
            theme_text_color="Custom", 
            text_color=[0.8, 0.2, 0.2, 1],  # Red color for emphasis
            font_style="Caption",
            size_hint_y=None, 
            height=dp(20)
        )
        
        # Add all fields to layout
        layout.add_widget(first_name_label)
        layout.add_widget(self.first_name_input)
        layout.add_widget(last_name_label)
        layout.add_widget(self.last_name_input)
        layout.add_widget(price_label)
        layout.add_widget(self.price_input)
        layout.add_widget(role_label)
        layout.add_widget(role_dropdown_box)
        layout.add_widget(MDBoxLayout(size_hint_y=None, height=dp(5)))  # Small spacer
        layout.add_widget(new_role_label)
        layout.add_widget(new_role_box)
        layout.add_widget(MDBoxLayout(size_hint_y=None, height=dp(10)))  # Spacer
        layout.add_widget(required_note)
        
        self.dialog = MDDialog(
            title="Add New Employee",
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

    
    def add_new_role_inline(self):
        """Add a new role directly from the employee dialog"""
        new_role = self.new_role_input.text.strip()
        
        if not new_role:
            # Show error in the text field
            self.new_role_input.error = True
            return
        
        # Reset error state if any
        self.new_role_input.error = False
        
        # Add the new role to the list if it's not already there
        if new_role not in self.employee_roles:
            # Add to the list in memory
            self.employee_roles.append(new_role)
            # Sort roles alphabetically
            self.employee_roles.sort()
            
            # Add to the database
            c = self.conn.cursor()
            try:
                c.execute("INSERT INTO roles (name) VALUES (?)", (new_role,))
                self.conn.commit()
            except sqlite3.IntegrityError:
                # Role already exists in database
                pass
        
        # Select this role for the employee
        self.role_selected = new_role
        
        # Update the role button text
        self.role_menu_button.text = new_role
        
        # Clear the new role input
        self.new_role_input.text = ""
    
    def save_employee(self):
        first_name = self.first_name_input.text.strip()
        last_name = self.last_name_input.text.strip()
        price_text = self.price_input.text.strip()
        
        # Validate all required fields
        missing_fields = []
        
        if not first_name:
            missing_fields.append("First Name")
            self.first_name_input.error = True
        else:
            self.first_name_input.error = False
        
        if not last_name:
            missing_fields.append("Last Name")
            self.last_name_input.error = True
        else:
            self.last_name_input.error = False
        
        if not price_text:
            missing_fields.append("Price per hour")
            self.price_input.error = True
        else:
            self.price_input.error = False
        
        # Check if role is selected
        if not hasattr(self, 'role_selected') or self.role_selected is None:
            missing_fields.append("Role")
            # Can't set error on button, but add to missing fields list
        
        # If any fields are missing, show error and return
        if missing_fields:
            error_message = "Please fill in the following required fields:\n• " + "\n• ".join(missing_fields)
            alert = MDDialog(
                title="Missing Information",
                text=error_message,
                buttons=[MDRaisedButton(
                    text="OK", 
                    on_release=lambda x: alert.dismiss(),
                    md_bg_color=[0.36, 0.65, 0.82, 1], 
                    text_color=[1, 1, 1, 1]
                )]
            )
            alert.open()
            return
        
        # Validate price as a number
        try:
            price_per_hour = float(price_text)
            if price_per_hour < 0:
                self.price_input.error = True
                alert = MDDialog(
                    title="Invalid Price",
                    text="Price per hour cannot be negative.",
                    buttons=[MDRaisedButton(
                        text="OK", 
                        on_release=lambda x: alert.dismiss(),
                        md_bg_color=[0.36, 0.65, 0.82, 1], 
                        text_color=[1, 1, 1, 1]
                    )]
                )
                alert.open()
                return
        except ValueError:
            self.price_input.error = True
            alert = MDDialog(
                title="Invalid Price",
                text="Price per hour must be a valid number.",
                buttons=[MDRaisedButton(
                    text="OK", 
                    on_release=lambda x: alert.dismiss(),
                    md_bg_color=[0.36, 0.65, 0.82, 1], 
                    text_color=[1, 1, 1, 1]
                )]
            )
            alert.open()
            return
        
        # All validation passed, save the employee
        role = self.role_selected
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO employees (first_name, last_name, role, price_per_hour) VALUES (?, ?, ?, ?)",
            (first_name, last_name, role, price_per_hour)
        )
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
        c.execute("SELECT first_name, last_name FROM employees WHERE id = ?", (employee_id,))
        first_name, last_name = c.fetchone()
        employee_name = f"{first_name} {last_name}".strip()
        
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
     
    def clock_out_and_refresh(self, employee_id, entry_id):
        """Clock out an employee and refresh the employee list to update buttons"""
        # First clock out the employee
        clock_out_time = datetime.now().isoformat()
        c = self.conn.cursor()
        
        # Get employee name for confirmation
        c.execute("SELECT first_name, last_name FROM employees WHERE id = ?", (employee_id,))
        first_name, last_name = c.fetchone()
        employee_name = f"{first_name} {last_name}".strip()
        
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
                    on_release=lambda x: self.on_employee_clock_out_dialog_close(clock_out_dialog)
                )
            ]
        )
        clock_out_dialog.open()

    def on_employee_clock_out_dialog_close(self, dialog):
        """Handle dialog close and refresh employees"""
        dialog.dismiss()
        # Refresh the employee list to update the buttons
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
            SELECT e.first_name, e.last_name, e.role, t.clock_in, t.clock_out, t.id, e.id 
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
        for first_name, last_name, role, clock_in, clock_out, entry_id, employee_id in rows:
            # Combine first and last name
            name = f"{first_name} {last_name}".strip()
            
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
                else:
                    clock_out_time = "Still clocked in"
                    status = "Currently active"
                    bg_color = [0.95, 1, 0.95, 1]  # Light green for active shifts
                
                # Use the same height for all entries
                entry_height = dp(70)
                
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
                
                # Add the entry to the list
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
            on_release=lambda x: self.show_employee_menu_for_reports()
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
        
    def show_employee_menu_for_reports(self):
        """Show dropdown menu of employees for reporting."""
        # First get all employees
        c = self.conn.cursor()
        c.execute("SELECT id, first_name, last_name FROM employees ORDER BY last_name, first_name")
        employees = c.fetchall()
        
        # Create menu items list with "All Employees" option first
        menu_items = [
            {
                "text": "All Employees",
                "viewclass": "OneLineListItem",
                "on_release": lambda: self.select_employee_for_report(None, "All Employees")
            }
        ]
        
        # Add each employee as an option
        for emp_id, first_name, last_name in employees:
            # Combine names for display
            full_name = f"{first_name} {last_name}".strip()
            menu_items.append(
                {
                    "text": full_name,
                    "viewclass": "OneLineListItem",
                    "on_release": lambda eid=emp_id, n=full_name: self.select_employee_for_report(eid, n)
                }
            )
        
        # Create and open the dropdown menu
        self.employee_menu = MDDropdownMenu(
            caller=self.employee_spinner_btn,
            items=menu_items,
            width_mult=4
        )
        self.employee_menu.open()
    
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
        
        # Build query using first_name and last_name instead of name
        query = '''
            SELECT e.first_name, e.last_name, e.role, t.clock_in, t.clock_out, t.id, e.id 
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
        for i, (first_name, last_name, role, clock_in, clock_out, _, employee_id) in enumerate(rows):
            # Combine first and last name
            name = f"{first_name} {last_name}".strip()
            
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

    def generate_todays_report(self):
        """Preset the reports page with today's date and generate report."""
        # First navigate to reports page
        self.show_reports()
        
        # Set today's date
        today = datetime.now().strftime("%Y-%m-%d")
        self.date_from.text = today
        self.date_to.text = today
        
        # Generate the report
        self.generate_report()

    def add_report_summary(self, rows):
        # Calculate summary statistics
        total_shifts = len(rows)
        total_hours = 0
        completed_shifts = 0
        
        # Process data for summary
        role_hours = {}
        
        for first_name, last_name, role, clock_in, clock_out, _, employee_id in rows:
            # Combine names for display
            name = f"{first_name} {last_name}".strip()
            
            if clock_in and clock_out:
                duration = datetime.fromisoformat(clock_out) - datetime.fromisoformat(clock_in)
                hours = duration.total_seconds() / 3600
                total_hours += hours
                completed_shifts += 1
                    
                # By role
                if role in role_hours:
                    role_hours[role] += hours
                else:
                    role_hours[role] = hours
        
        # Create summary box
        summary_box = BorderedBox(
            orientation="vertical",
            size_hint_y=None,
            height=dp(120),  # Reduced height since we removed a section
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
        
        # Build query - now updated to include first_name and last_name
        query = '''
            SELECT e.first_name, e.last_name, e.role, t.clock_in, t.clock_out, e.id, e.price_per_hour
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
        
        # Calculate summary statistics
        total_shifts = len(rows)
        total_hours = 0
        completed_shifts = 0
        total_earnings = 0
        
        # Process data for summary
        role_hours = {}
        role_earnings = {}
        
        # Make sure to unpack the correct number of columns
        for first_name, last_name, role, clock_in, clock_out, employee_id, price_per_hour in rows:
            # Combine names for display
            name = f"{first_name} {last_name}".strip()
            
            if clock_in and clock_out:
                duration = datetime.fromisoformat(clock_out) - datetime.fromisoformat(clock_in)
                hours = duration.total_seconds() / 3600
                total_hours += hours
                completed_shifts += 1
                
                # Calculate earnings for this shift
                earnings = hours * price_per_hour
                total_earnings += earnings
                    
                # By role
                if role in role_hours:
                    role_hours[role] += hours
                    role_earnings[role] = role_earnings.get(role, 0) + earnings
                else:
                    role_hours[role] = hours
                    role_earnings[role] = earnings
        
        try:
            # Generate a filename with timestamp
            import os
            import csv
            
            # Create a desktop path for the CSV file
            home_dir = os.path.expanduser("~")
            desktop_dir = os.path.join(home_dir, "Desktop")
            date_str = datetime.now().strftime("%Y%m%d")
            
            # Create a more straightforward filename based on your criteria
            if hasattr(self, 'selected_employee_id') and self.selected_employee_id is not None:
                # For a single employee report
                employee_name = self.employee_spinner_btn.text.replace(" ", "_")
                filename = f"{employee_name}'s_Report_{date_str}.csv"
            elif hasattr(self, 'selected_role') and self.selected_role is not None:
                # For a specific role report
                role_name = self.selected_role.replace(" ", "_")
                filename = f"{role_name}_Role_Report_{date_str}.csv"
            else:
                # For all employees
                filename = f"All_Employees_Report_{date_str}.csv"
            
            # Full path for the file
            file_path = os.path.join(desktop_dir, filename)
            
            # Create CSV file
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write summary statistics first
                writer.writerow(['Summary Statistics'])
                writer.writerow(['Total Shifts', str(total_shifts)])
                writer.writerow(['Completed Shifts', str(completed_shifts)])
                writer.writerow(['Total Hours', f"{total_hours:.2f}"])
                writer.writerow(['Total Earnings', f"${total_earnings:.2f}"])
                
                # Add hours and earnings by role
                if role_hours:
                    writer.writerow([''])
                    writer.writerow(['Hours and Earnings by Role:'])
                    for role in sorted(role_hours.keys()):
                        writer.writerow([
                            role, 
                            f"{role_hours[role]:.2f}h", 
                            f"${role_earnings.get(role, 0):.2f}"
                        ])
                
                # Add a separator
                writer.writerow([''])
                writer.writerow([''])  # Extra blank line for separation
                
                # Write header for detailed data
                writer.writerow(['Name', 'Role', 'Clock In', 'Clock Out', 'Duration (Hours)', 'Rate ($/hr)', 'Earnings ($)'])
                
                # Write data
                for first_name, last_name, role, clock_in, clock_out, employee_id, price_per_hour in rows:
                    # Combine names for display
                    name = f"{first_name} {last_name}".strip()
                    
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
                        
                        # Calculate earnings for this shift
                        earnings = duration * price_per_hour
                        earnings_fmt = f"{earnings:.2f}"
                    else:
                        clock_out_fmt = ""
                        duration_fmt = ""
                        earnings_fmt = ""
                    
                    writer.writerow([
                        name, 
                        role, 
                        clock_in_fmt, 
                        clock_out_fmt, 
                        duration_fmt, 
                        f"{price_per_hour:.2f}", 
                        earnings_fmt
                    ])
            
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