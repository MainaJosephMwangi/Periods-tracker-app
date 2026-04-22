"""
CycleCare - Menstrual Cycle Tracker & Shop
A comprehensive app for tracking menstrual cycles and purchasing wellness products
STANDALONE VERSION - All modules embedded in one file
"""
import flet as ft
from datetime import datetime, timedelta
import calendar as cal
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import uuid

# ============================================================================
# DATABASE MODULE
# ============================================================================

class Database:
    """SQLite database manager for CycleCare"""
    
    def __init__(self, db_path: str = "cyclecare.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY,
                cycle_length INTEGER DEFAULT 28,
                period_length INTEGER DEFAULT 5,
                last_period_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS period_entries (
                id INTEGER PRIMARY KEY,
                date TEXT UNIQUE,
                flow_intensity TEXT DEFAULT 'medium',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS symptoms (
                id INTEGER PRIMARY KEY,
                date TEXT,
                symptom_type TEXT,
                intensity INTEGER DEFAULT 3,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cart_items (
                id INTEGER PRIMARY KEY,
                product_id TEXT,
                product_name TEXT,
                price REAL,
                quantity INTEGER DEFAULT 1,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                order_number TEXT UNIQUE,
                total_price REAL,
                status TEXT DEFAULT 'pending',
                delivery_address TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY,
                order_id INTEGER,
                product_name TEXT,
                quantity INTEGER,
                price REAL,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_settings(self) -> Dict:
        """Get user settings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT cycle_length, period_length, last_period_date FROM settings LIMIT 1')
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'cycle_length': result[0],
                'period_length': result[1],
                'last_period_date': result[2]
            }
        return {
            'cycle_length': 28,
            'period_length': 5,
            'last_period_date': None
        }
    
    def save_settings(self, cycle_length: int, period_length: int, last_period_date: str):
        """Save user settings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM settings')
        if cursor.fetchone():
            cursor.execute('''
                UPDATE settings 
                SET cycle_length = ?, period_length = ?, last_period_date = ?
            ''', (cycle_length, period_length, last_period_date))
        else:
            cursor.execute('''
                INSERT INTO settings (cycle_length, period_length, last_period_date)
                VALUES (?, ?, ?)
            ''', (cycle_length, period_length, last_period_date))
        
        conn.commit()
        conn.close()
    
    def add_period_entry(self, date: str, flow_intensity: str = "medium", notes: str = ""):
        """Add period entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO period_entries (date, flow_intensity, notes)
                VALUES (?, ?, ?)
            ''', (date, flow_intensity, notes))
            conn.commit()
        finally:
            conn.close()
    
    def get_period_entries(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get period entries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if start_date and end_date:
            cursor.execute('''
                SELECT date, flow_intensity, notes FROM period_entries
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC
            ''', (start_date, end_date))
        else:
            cursor.execute('SELECT date, flow_intensity, notes FROM period_entries ORDER BY date DESC')
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {'date': r[0], 'flow_intensity': r[1], 'notes': r[2]}
            for r in results
        ]
    
    def add_symptom(self, date: str, symptom_type: str, intensity: int = 3, notes: str = ""):
        """Add symptom entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO symptoms (date, symptom_type, intensity, notes)
            VALUES (?, ?, ?, ?)
        ''', (date, symptom_type, intensity, notes))
        conn.commit()
        conn.close()
    
    def get_symptoms(self, date: str = None) -> List[Dict]:
        """Get symptoms for a specific date or all symptoms"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if date:
            cursor.execute('''
                SELECT date, symptom_type, intensity, notes FROM symptoms
                WHERE date = ?
                ORDER BY created_at DESC
            ''', (date,))
        else:
            cursor.execute('SELECT date, symptom_type, intensity, notes FROM symptoms ORDER BY date DESC')
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {'date': r[0], 'symptom_type': r[1], 'intensity': r[2], 'notes': r[3]}
            for r in results
        ]
    
    def add_to_cart(self, product_id: str, product_name: str, price: float, quantity: int = 1):
        """Add item to cart"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT quantity FROM cart_items WHERE product_id = ?', (product_id,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE cart_items SET quantity = quantity + ? WHERE product_id = ?
            ''', (quantity, product_id))
        else:
            cursor.execute('''
                INSERT INTO cart_items (product_id, product_name, price, quantity)
                VALUES (?, ?, ?, ?)
            ''', (product_id, product_name, price, quantity))
        
        conn.commit()
        conn.close()
    
    def get_cart_items(self) -> List[Dict]:
        """Get all cart items"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, product_id, product_name, price, quantity FROM cart_items')
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': r[0],
                'product_id': r[1],
                'product_name': r[2],
                'price': r[3],
                'quantity': r[4]
            }
            for r in results
        ]
    
    def remove_from_cart(self, product_id: str):
        """Remove item from cart"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cart_items WHERE product_id = ?', (product_id,))
        conn.commit()
        conn.close()
    
    def clear_cart(self):
        """Clear all cart items"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cart_items')
        conn.commit()
        conn.close()
    
    def create_order(self, order_number: str, total_price: float, delivery_address: str, items: List[Dict]):
        """Create an order"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO orders (order_number, total_price, delivery_address, status)
            VALUES (?, ?, ?, 'pending')
        ''', (order_number, total_price, delivery_address))
        
        order_id = cursor.lastrowid
        
        for item in items:
            cursor.execute('''
                INSERT INTO order_items (order_id, product_name, quantity, price)
                VALUES (?, ?, ?, ?)
            ''', (order_id, item['product_name'], item['quantity'], item['price']))
        
        conn.commit()
        conn.close()
        
        return order_number
    
    def get_orders(self) -> List[Dict]:
        """Get all orders"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, order_number, total_price, status, delivery_address, created_at
            FROM orders
            ORDER BY created_at DESC
        ''')
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': r[0],
                'order_number': r[1],
                'total_price': r[2],
                'status': r[3],
                'delivery_address': r[4],
                'created_at': r[5]
            }
            for r in results
        ]

# ============================================================================
# CYCLE MODULE
# ============================================================================

@dataclass
class CycleSettings:
    """User's cycle settings"""
    cycle_length: int = 28
    period_length: int = 5
    last_period_date: Optional[datetime] = None
    
    def to_dict(self):
        return asdict(self)

@dataclass
class PeriodEntry:
    """Record of a period"""
    date: datetime
    flow_intensity: str = "medium"
    notes: str = ""
    
    def to_dict(self):
        return {
            "date": self.date.isoformat(),
            "flow_intensity": self.flow_intensity,
            "notes": self.notes
        }

@dataclass
class Symptom:
    """Daily symptom tracking"""
    date: datetime
    symptom_type: str
    intensity: int = 3
    notes: str = ""
    
    def to_dict(self):
        return {
            "date": self.date.isoformat(),
            "symptom_type": self.symptom_type,
            "intensity": self.intensity,
            "notes": self.notes
        }

class CycleCalculator:
    """Calculate cycle phases and predictions"""
    
    PHASES = {
        "menstrual": {"color": "#EF4444", "name": "Menstrual"},
        "follicular": {"color": "#EC4899", "name": "Follicular"},
        "ovulation": {"color": "#F59E0B", "name": "Ovulation"},
        "luteal": {"color": "#8B5CF6", "name": "Luteal"}
    }
    
    @staticmethod
    def get_phase(settings: CycleSettings, target_date: datetime) -> tuple:
        """Determine cycle phase for a given date"""
        if not settings.last_period_date:
            return "unknown", "#999999"
        
        days_into_cycle = (target_date - settings.last_period_date).days % settings.cycle_length
        
        menstrual_end = settings.period_length
        follicular_end = settings.cycle_length // 2 - 2
        ovulation_end = settings.cycle_length // 2 + 2
        
        if days_into_cycle < menstrual_end:
            phase = "menstrual"
        elif days_into_cycle < follicular_end:
            phase = "follicular"
        elif days_into_cycle < ovulation_end:
            phase = "ovulation"
        else:
            phase = "luteal"
        
        phase_info = CycleCalculator.PHASES.get(phase, {})
        return phase, phase_info.get("color", "#999999")
    
    @staticmethod
    def get_next_period(settings: CycleSettings) -> Optional[datetime]:
        """Calculate the next predicted period date"""
        if not settings.last_period_date:
            return None
        
        return settings.last_period_date + timedelta(days=settings.cycle_length)
    
    @staticmethod
    def get_next_ovulation(settings: CycleSettings) -> Optional[datetime]:
        """Calculate the next predicted ovulation date"""
        if not settings.last_period_date:
            return None
        
        ovulation_day = settings.cycle_length // 2
        return settings.last_period_date + timedelta(days=ovulation_day)
    
    @staticmethod
    def get_cycle_day(settings: CycleSettings) -> int:
        """Get current day in cycle"""
        if not settings.last_period_date:
            return 0
        
        today = datetime.now()
        days_since_period = (today - settings.last_period_date).days
        return (days_since_period % settings.cycle_length) + 1

# ============================================================================
# PRODUCTS MODULE
# ============================================================================

@dataclass
class Product:
    """Product model"""
    id: str
    name: str
    category: str
    price: float
    description: str
    rating: float = 4.5
    reviews: int = 0
    in_stock: bool = True
    image_emoji: str = "📦"
    image_url: str = ""

PRODUCTS = [
    Product(id="pad_001", name="Ultra Thin Pads (20 count)", category="Sanitary Pads", price=4.99, description="Ultra-thin, comfortable sanitary pads with wings for maximum protection", rating=4.8, reviews=245, image_emoji="📋", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/sanitary_pads-EwpRaytSrjuXjmCprz4uDY.webp"),
    Product(id="pad_002", name="Heavy Flow Pads (16 count)", category="Sanitary Pads", price=5.49, description="Extra absorbent pads designed for heavy flow days", rating=4.6, reviews=189, image_emoji="📋", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/sanitary_pads-EwpRaytSrjuXjmCprz4uDY.webp"),
    Product(id="pad_003", name="Organic Cotton Pads (12 count)", category="Sanitary Pads", price=7.99, description="100% organic cotton pads, hypoallergenic and eco-friendly", rating=4.9, reviews=312, image_emoji="📋", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/organic_pads-EVHAn6zxeMPd2Pp979zrJK.webp"),
    Product(id="tampon_001", name="Regular Tampons (40 count)", category="Tampons", price=5.99, description="Comfortable regular tampons with applicator", rating=4.7, reviews=198, image_emoji="🔹", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/tampons-gRZ8Gnnjimfg7G8PPoX3yN.webp"),
    Product(id="tampon_002", name="Super Tampons (36 count)", category="Tampons", price=6.49, description="Super absorbent tampons for heavy flow", rating=4.5, reviews=156, image_emoji="🔹", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/tampons-gRZ8Gnnjimfg7G8PPoX3yN.webp"),
    Product(id="tampon_003", name="Organic Tampons (32 count)", category="Tampons", price=8.99, description="100% organic cotton tampons, plastic-free applicator", rating=4.8, reviews=267, image_emoji="🔹", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/tampons-gRZ8Gnnjimfg7G8PPoX3yN.webp"),
    Product(id="cup_001", name="Silicone Menstrual Cup", category="Menstrual Cups", price=24.99, description="Reusable silicone menstrual cup, eco-friendly alternative", rating=4.7, reviews=423, image_emoji="🥤", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/menstrual_cup-a4mArAW5k4cf6tUAQJ8bVA.webp"),
    Product(id="cup_002", name="Premium Menstrual Cup Set", category="Menstrual Cups", price=34.99, description="Set of 2 menstrual cups in different sizes with carrying case", rating=4.9, reviews=567, image_emoji="🥤", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/menstrual_cup-a4mArAW5k4cf6tUAQJ8bVA.webp"),
    Product(id="underwear_001", name="Period Underwear (2 pack)", category="Period Underwear", price=39.99, description="Leak-proof period underwear, comfortable and discreet", rating=4.6, reviews=289, image_emoji="👖", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/period_underwear-Xuhc363GfREcTGAGwYmLRx.webp"),
    Product(id="underwear_002", name="Period Underwear (5 pack)", category="Period Underwear", price=89.99, description="5-pack of leak-proof period underwear in various styles", rating=4.8, reviews=445, image_emoji="👖", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/period_underwear-Xuhc363GfREcTGAGwYmLRx.webp"),
    Product(id="hotbottle_001", name="Electric Heating Pad", category="Pain Relief", price=29.99, description="Rechargeable electric heating pad for period cramps", rating=4.7, reviews=334, image_emoji="🔥", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/heating_pad-PN3QQte6UngD8SD3K7mZn4.webp"),
    Product(id="hotbottle_002", name="Hot Water Bottle", category="Pain Relief", price=14.99, description="Traditional hot water bottle with soft cover", rating=4.5, reviews=198, image_emoji="🔥", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/hot_water_bottle-6n94cpMyiS4u9A6rAMYfcQ.webp"),
    Product(id="hotbottle_003", name="Microwaveable Heat Pack", category="Pain Relief", price=12.99, description="Reusable microwaveable heat pack for cramp relief", rating=4.6, reviews=267, image_emoji="🔥", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/heat_pack-F8wrgxTSaeLC2h2iXmoaos.webp"),
    Product(id="wellness_001", name="Period Tea Blend (30 bags)", category="Wellness", price=9.99, description="Herbal tea blend to support cycle wellness", rating=4.7, reviews=156, image_emoji="🫖", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/tea_blend-Ji73Fo8jNzCj5zQG7C7WvR.webp"),
    Product(id="wellness_002", name="Cycle Vitamins (60 capsules)", category="Wellness", price=19.99, description="Specially formulated vitamins for cycle support", rating=4.8, reviews=289, image_emoji="💊", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/vitamins-HZubVaBy9mUfY3EwR9NH4u.webp"),
    Product(id="wellness_003", name="Magnesium Supplement (90 tablets)", category="Wellness", price=14.99, description="High-quality magnesium to reduce cramps and support relaxation", rating=4.6, reviews=234, image_emoji="💊", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/magnesium-7Zrkyvr4LFHgMT7kE6UtiH.webp"),
    Product(id="wellness_004", name="Aromatherapy Roller", category="Wellness", price=11.99, description="Essential oil roller blend for period comfort", rating=4.5, reviews=145, image_emoji="🧴", image_url="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/aromatherapy_roller-6PuwQwJUe2uFBgipso5qsb.webp"),
]

def get_products_by_category(category: str = None) -> List[Product]:
    if category:
        return [p for p in PRODUCTS if p.category == category]
    return PRODUCTS

def get_categories() -> List[str]:
    return sorted(list(set(p.category for p in PRODUCTS)))

def get_product_by_id(product_id: str) -> Product:
    for product in PRODUCTS:
        if product.id == product_id:
            return product
    return None

def search_products(query: str) -> List[Product]:
    query = query.lower()
    return [p for p in PRODUCTS if query in p.name.lower() or query in p.description.lower()]

# ============================================================================
# SHOP MODULE
# ============================================================================

@dataclass
class CartItem:
    """Shopping cart item"""
    product_id: str
    product_name: str
    price: float
    quantity: int
    
    def get_total(self) -> float:
        return self.price * self.quantity

@dataclass
class Order:
    """Order information"""
    order_number: str
    items: List[CartItem]
    delivery_address: str
    phone_number: str
    total_price: float
    status: str = "pending"
    created_at: str = None
    estimated_delivery: str = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

class ShoppingCart:
    """Shopping cart management"""
    
    def __init__(self):
        self.items: List[CartItem] = []
    
    def add_item(self, product_id: str, product_name: str, price: float, quantity: int = 1):
        for item in self.items:
            if item.product_id == product_id:
                item.quantity += quantity
                return
        self.items.append(CartItem(product_id, product_name, price, quantity))
    
    def remove_item(self, product_id: str):
        self.items = [item for item in self.items if item.product_id != product_id]
    
    def update_quantity(self, product_id: str, quantity: int):
        for item in self.items:
            if item.product_id == product_id:
                if quantity <= 0:
                    self.remove_item(product_id)
                else:
                    item.quantity = quantity
                return
    
    def clear(self):
        self.items = []
    
    def get_subtotal(self) -> float:
        return sum(item.get_total() for item in self.items)
    
    def get_shipping_cost(self) -> float:
        subtotal = self.get_subtotal()
        if subtotal == 0:
            return 0
        elif subtotal < 50:
            return 5.99
        elif subtotal < 100:
            return 3.99
        else:
            return 0
    
    def get_tax(self) -> float:
        return self.get_subtotal() * 0.08
    
    def get_total(self) -> float:
        return self.get_subtotal() + self.get_tax() + self.get_shipping_cost()
    
    def get_item_count(self) -> int:
        return sum(item.quantity for item in self.items)
    
    def is_empty(self) -> bool:
        return len(self.items) == 0

class OrderProcessor:
    """Process and manage orders"""
    
    @staticmethod
    def create_order(cart: ShoppingCart, delivery_address: str, phone_number: str) -> Optional[Order]:
        if cart.is_empty():
            return None
        
        order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        order = Order(
            order_number=order_number,
            items=cart.items.copy(),
            delivery_address=delivery_address,
            phone_number=phone_number,
            total_price=cart.get_total()
        )
        
        return order
    
    @staticmethod
    def validate_order(order: Order) -> tuple:
        if not order.items:
            return False, "Cart is empty"
        
        if not order.delivery_address or len(order.delivery_address.strip()) < 5:
            return False, "Invalid delivery address"
        
        if not order.phone_number or len(order.phone_number.strip()) < 7:
            return False, "Invalid phone number"
        
        if order.total_price <= 0:
            return False, "Invalid order total"
        
        return True, "Order is valid"

class PaymentProcessor:
    """Process payments (mock implementation)"""
    
    @staticmethod
    def validate_card(card_number: str, expiry: str, cvv: str) -> tuple:
        card_number = card_number.replace(" ", "")
        
        if not card_number.isdigit() or len(card_number) != 16:
            return False, "Invalid card number"
        
        if "/" not in expiry or len(expiry) != 5:
            return False, "Invalid expiry format (use MM/YY)"
        
        try:
            month, year = expiry.split("/")
            month = int(month)
            year = int(year)
            
            if month < 1 or month > 12:
                return False, "Invalid month"
            
            if year < 24:
                return False, "Card expired"
        except ValueError:
            return False, "Invalid expiry date"
        
        if not cvv.isdigit() or len(cvv) < 3 or len(cvv) > 4:
            return False, "Invalid CVV"
        
        return True, "Card is valid"
    
    @staticmethod
    def process_payment(order: Order, card_number: str, expiry: str, cvv: str) -> tuple:
        is_valid, message = PaymentProcessor.validate_card(card_number, expiry, cvv)
        
        if not is_valid:
            return False, message
        
        order.status = "confirmed"
        
        return True, f"Payment processed successfully. Order #{order.order_number} confirmed!"

# ============================================================================
# MAIN APPLICATION
# ============================================================================

class CycleCareApp:
    def __init__(self):
        self.db = Database()
        self.settings = self._load_settings()
        self.current_view = "home"
        self.selected_date = datetime.now()
        self.cart = ShoppingCart()
        self.cart_items = []
        
    def _load_settings(self):
        """Load settings from database"""
        db_settings = self.db.get_settings()
        last_period = db_settings['last_period_date']
        
        if last_period:
            last_period = datetime.strptime(last_period, '%Y-%m-%d')
        
        return CycleSettings(
            cycle_length=db_settings['cycle_length'],
            period_length=db_settings['period_length'],
            last_period_date=last_period
        )
    
    def build(self, page: ft.Page):
        """Build the main UI"""
        page.title = "CycleCare - Menstrual Cycle Tracker & Shop"
        page.window.width = 400
        page.window.height = 800
        page.window.resizable = False
        
        self.main_content = ft.Container(expand=True)
        
        def on_tab_change(e):
            selected_index = e.control.selected_index
            if selected_index == 0:
                self.show_home_view(page)
            elif selected_index == 1:
                self.show_calendar_view(page)
            elif selected_index == 2:
                self.show_shop_view(page)
            elif selected_index == 3:
                self.show_orders_view(page)
            elif selected_index == 4:
                self.show_profile_view(page)
        
        self.bottom_nav = ft.NavigationBar(
            on_change=on_tab_change,
            destinations=[
                ft.NavigationBarDestination(icon=ft.icons.HOME, label="Home"),
                ft.NavigationBarDestination(icon=ft.icons.CALENDAR_MONTH, label="Calendar"),
                ft.NavigationBarDestination(icon=ft.icons.SHOPPING_CART, label="Shop"),
                ft.NavigationBarDestination(icon=ft.icons.RECEIPT, label="Orders"),
                ft.NavigationBarDestination(icon=ft.icons.PERSON, label="Profile"),
            ]
        )
        
        page.add(
            ft.Column(
                controls=[
                    self.main_content,
                    self.bottom_nav,
                ],
                expand=True,
                spacing=0
            )
        )
        
        self.show_home_view(page)
    
    def show_home_view(self, page: ft.Page):
        """Display home view"""
        self.current_view = "home"
        
        if not self.settings.last_period_date:
            content = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Welcome to CycleCare!", size=24, weight="bold", color="#D946A6"),
                        ft.Text("Please set up your cycle information in the Profile tab to get started.", size=14, color="#4B5563"),
                        ft.ElevatedButton(
                            "Go to Profile",
                            icon=ft.icons.PERSON,
                            color="white",
                            bgcolor="#D946A6",
                            expand=True,
                            on_click=lambda e: (setattr(self.bottom_nav, 'selected_index', 4), page.update())
                        ),
                    ],
                    spacing=20,
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                padding=20,
                expand=True
            )
        else:
            cycle_day = CycleCalculator.get_cycle_day(self.settings)
            phase, color = CycleCalculator.get_phase(self.settings, datetime.now())
            next_period = CycleCalculator.get_next_period(self.settings)
            next_ovulation = CycleCalculator.get_next_ovulation(self.settings)
            
            days_until_period = (next_period - datetime.now()).days if next_period else 0
            
            content = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Cycle Status", size=24, weight="bold", color="#D946A6", offset=ft.transform.Offset(0.02, 0)),
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Row(
                                            controls=[
                                                ft.Text(f"Day {cycle_day}", size=32, weight="bold", color=color),
                                                ft.Column(
                                                    controls=[
                                                        ft.Text(phase.capitalize(), size=14, weight="bold", color=color),
                                                        ft.Text(f"{days_until_period} days until next period", size=12, color="#4B5563"),
                                                    ]
                                                ),
                                            ]
                                        ),
                                    ],
                                    spacing=10
                                ),
                                padding=15,
                            ),
                            margin=8
                        ),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton(
                                    "Log Period",
                                    icon=ft.icons.ADD,
                                    color="white",
                                    bgcolor="#EC4899",
                                    expand=True,
                                    on_click=lambda e: self.show_log_period_dialog(page)
                                ),
                                ft.ElevatedButton(
                                    "Add Symptom",
                                    icon=ft.icons.ADD,
                                    color="white",
                                    bgcolor="#A855F7",
                                    expand=True,
                                    on_click=lambda e: self.show_add_symptom_dialog(page)
                                ),
                            ],
                            spacing=10
                        ),
                        ft.Divider(height=20),
                        ft.Text("Learn About Your Period", size=16, weight="bold", color="#D946A6"),
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Image(
                                            src="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/menstrual_cycle_phases-Gz7M43JSVHVYtBMft8aUvY.webp",
                                            width=280,
                                            height=140,
                                            fit=ft.ImageFit.CONTAIN,
                                            border_radius=ft.border_radius.all(8),
                                        ),
                                        ft.Text("The 4 Phases of Your Cycle", size=13, weight="bold", color="#1F2937"),
                                        ft.Text("Your cycle has 4 phases: Menstrual, Follicular, Ovulation, and Luteal. Each brings different hormonal changes and energy levels.", size=10, color="#4B5563"),
                                    ],
                                    spacing=8
                                ),
                                padding=12,
                            ),
                            margin=8
                        ),
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Image(
                                            src="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/period_facts-Pboko78Zfso2KhNvkdgg2o.webp",
                                            width=280,
                                            height=140,
                                            fit=ft.ImageFit.CONTAIN,
                                            border_radius=ft.border_radius.all(8),
                                        ),
                                        ft.Text("Period Facts", size=13, weight="bold", color="#1F2937"),
                                        ft.Text("Average cycle: 28 days | Duration: 3-7 days | Blood loss: 30-40ml. Hormones fluctuate throughout affecting mood and energy.", size=10, color="#4B5563"),
                                    ],
                                    spacing=8
                                ),
                                padding=12,
                            ),
                            margin=8
                        ),
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Image(
                                            src="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/period_symptoms-W6xf2M4PZLSHzmf5pbX6at.webp",
                                            width=280,
                                            height=140,
                                            fit=ft.ImageFit.CONTAIN,
                                            border_radius=ft.border_radius.all(8),
                                        ),
                                        ft.Text("Common Symptoms", size=13, weight="bold", color="#1F2937"),
                                        ft.Text("Cramps, bloating, fatigue, mood changes, headaches, and breast tenderness are all normal. Tracking helps you manage them.", size=10, color="#4B5563"),
                                    ],
                                    spacing=8
                                ),
                                padding=12,
                            ),
                            margin=8
                        ),
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Image(
                                            src="https://d2xsxph8kpxj0f.cloudfront.net/310519663458597147/YbyVTRiEmAvuoHAuMFVPbV/period_health_tips-haWxeCSZ5BrkPYXDJwFvkQ.webp",
                                            width=280,
                                            height=140,
                                            fit=ft.ImageFit.CONTAIN,
                                            border_radius=ft.border_radius.all(8),
                                        ),
                                        ft.Text("Period Management Tips", size=13, weight="bold", color="#1F2937"),
                                        ft.Text("Stay hydrated, exercise, manage stress, eat nutritious foods, track your cycle, and get enough sleep for better well-being.", size=10, color="#4B5563"),
                                    ],
                                    spacing=8
                                ),
                                padding=12,
                            ),
                            margin=8
                        ),
                        ft.Divider(height=20),
                        ft.Text("Upcoming Events", size=16, weight="bold", color="#1F2937"),
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Row(
                                            controls=[
                                                ft.Text("🩸", size=20),
                                                ft.Column(
                                                    controls=[
                                                        ft.Text("Next Period", size=12, weight="bold"),
                                                        ft.Text(next_period.strftime("%B %d, %Y") if next_period else "Unknown", size=11, color="#4B5563"),
                                                    ]
                                                ),
                                            ]
                                        ),
                                        ft.Divider(height=10),
                                        ft.Row(
                                            controls=[
                                                ft.Text("🌙", size=20),
                                                ft.Column(
                                                    controls=[
                                                        ft.Text("Ovulation", size=12, weight="bold"),
                                                        ft.Text(next_ovulation.strftime("%B %d, %Y") if next_ovulation else "Unknown", size=11, color="#4B5563"),
                                                    ]
                                                ),
                                            ]
                                        ),
                                    ],
                                    spacing=8
                                ),
                                padding=12,
                            ),
                            margin=8
                        ),
                        ],
                        scroll=ft.ScrollMode.AUTO,
                        spacing=10,
                        expand=True,
                    ),
                padding=10,
                expand=True
            )
        
        self.main_content.content = content
        page.update()
    
    def show_calendar_view(self, page: ft.Page):
        """Display calendar view"""
        self.current_view = "calendar"
        
        today = datetime.now()
        year = today.year
        month = today.month
        
        calendar_days = []
        month_calendar = cal.monthcalendar(year, month)
        
        for week in month_calendar:
            week_row = []
            for day in week:
                if day == 0:
                    week_row.append(ft.Container(width=50, height=50))
                else:
                    date = datetime(year, month, day)
                    phase, color = CycleCalculator.get_phase(self.settings, date)
                    
                    day_button = ft.Container(
                        content=ft.Text(str(day), size=12, weight="bold", color="white", text_align=ft.TextAlign.CENTER),
                        width=50,
                        height=50,
                        bgcolor=color,
                        border_radius=5,
                        alignment=ft.alignment.center,
                        on_click=lambda e, d=day, m=month, y=year: self.show_day_details(page, d, m, y)
                    )
                    week_row.append(day_button)
            
            calendar_days.append(ft.Row(controls=week_row, spacing=5))
        
        period_entries = self.db.get_period_entries()
        period_text = "Period History:\n"
        for entry in period_entries[:5]:
            period_text += f"• {entry['date']}: {entry['flow_intensity']}\n"
        
        content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Calendar", size=24, weight="bold", color="#D946A6", offset=ft.transform.Offset(0.02, 0)),
                    ft.Text(f"{datetime(year, month, 1).strftime('%B %Y')}", size=16, weight="bold", color="#1F2937"),
                    ft.Row(
                        controls=[
                            ft.Text("Mon", size=10, weight="bold", text_align=ft.TextAlign.CENTER),
                            ft.Text("Tue", size=10, weight="bold", text_align=ft.TextAlign.CENTER),
                            ft.Text("Wed", size=10, weight="bold", text_align=ft.TextAlign.CENTER),
                            ft.Text("Thu", size=10, weight="bold", text_align=ft.TextAlign.CENTER),
                            ft.Text("Fri", size=10, weight="bold", text_align=ft.TextAlign.CENTER),
                            ft.Text("Sat", size=10, weight="bold", text_align=ft.TextAlign.CENTER),
                            ft.Text("Sun", size=10, weight="bold", text_align=ft.TextAlign.CENTER),
                        ],
                        spacing=5
                    ),
                    *calendar_days,
                    ft.Divider(height=20),
                    ft.Text(period_text, size=11, color="#1F2937"),
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=10,
                expand=True,
            ),
            padding=10,
            expand=True
        )
        
        self.main_content.content = content
        page.update()
    
    def show_shop_view(self, page: ft.Page):
        """Display shop view"""
        self.current_view = "shop"
        
        cart_count = self.cart.get_item_count()
        
        products = get_products_by_category()
        product_cards = []
        
        for product in products:
            product_image = ft.Image(
                src=product.image_url if product.image_url else "",
                width=100,
                height=100,
                fit=ft.ImageFit.COVER,
                border_radius=ft.border_radius.all(8),
            ) if product.image_url else ft.Container(
                width=100,
                height=100,
                bgcolor="#F5F5F5",
                border_radius=ft.border_radius.all(8),
                content=ft.Text(product.image_emoji, size=35, text_align=ft.TextAlign.CENTER),
                alignment=ft.alignment.center
            )
            
            product_card = ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            product_image,
                            ft.Text(product.name, size=10, weight="bold", color="#1F2937", max_lines=2),
                            ft.Text(product.category, size=9, color="#4B5563"),
                            ft.Row(
                                controls=[
                                    ft.Text(f"${product.price:.2f}", size=12, weight="bold", color="#EC4899"),
                                    ft.Text(f"⭐ {product.rating}", size=8, color="#4B5563"),
                                ]
                            ),
                            ft.ElevatedButton(
                                "Add to Cart",
                                icon=ft.icons.SHOPPING_CART,
                                color="white",
                                bgcolor="#EC4899",
                                expand=True,
                                on_click=lambda e, p=product: self.add_to_cart(page, p)
                            ),
                        ],
                        spacing=6,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    padding=10,
                ),
                margin=6
            )
            product_cards.append(product_card)
        
        # Create 4-column grid layout
        product_rows = []
        for i in range(0, len(product_cards), 4):
            row_items = []
            for j in range(4):
                if i + j < len(product_cards):
                    row_items.append(product_cards[i + j])
            if row_items:
                product_rows.append(
                    ft.Row(
                        controls=row_items,
                        spacing=5,
                        expand=True
                    )
                )
        
        view_cart_button = ft.ElevatedButton(
            f"View Cart ({cart_count})",
            icon=ft.icons.SHOPPING_CART,
            color="white",
                            bgcolor="#A855F7",
            expand=True,
            on_click=lambda e: self.show_cart_view(page)
        )
        
        content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Shop", size=24, weight="bold", color="#D946A6", offset=ft.transform.Offset(0.02, 0)),
                    ft.Column(
                        controls=product_rows,
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                        spacing=5
                    ),
                    ft.Container(content=view_cart_button, padding=ft.padding.only(left=10, right=10, bottom=10)),
                ],
                spacing=5,
                expand=True
            ),
            padding=10,
            expand=True
        )
        
        self.main_content.content = content
        page.update()
    
    def show_orders_view(self, page: ft.Page):
        """Display orders view"""
        self.current_view = "orders"
        
        orders = self.db.get_orders()
        order_cards = []
        
        if not orders:
            content = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Orders", size=24, weight="bold", color="#EC4899", offset=ft.transform.Offset(0.02, 0)),
                        ft.Container(
                            content=ft.Text("No orders yet", size=16, color="#4B5563", text_align=ft.TextAlign.CENTER),
                            expand=True,
                            alignment=ft.alignment.center
                        ),
                    ],
                    spacing=10,
                    expand=True
                ),
                padding=10,
                expand=True
            )
        else:
            for order in orders:
                order_card = ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Column(
                                            controls=[
                                                ft.Text(f"Order #{order['order_number']}", size=12, weight="bold", color="#1F2937"),
                                                ft.Text(f"${order['total_price']:.2f}", size=14, weight="bold", color="#EC4899"),
                                            ],
                                            expand=True
                                        ),
                                        ft.Text(order['status'].capitalize(), size=11, color="#A855F7", weight="bold"),
                                    ]
                                ),
                                ft.Text(f"Delivery: {order['delivery_address']}", size=10, color="#4B5563"),
                                ft.Text(f"Date: {order['created_at'][:10]}", size=10, color="#4B5563"),
                            ],
                            spacing=5
                        ),
                        padding=12,
                    ),
                    margin=8
                )
                order_cards.append(order_card)
            
            content = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Orders", size=24, weight="bold", color="#EC4899", offset=ft.transform.Offset(0.02, 0)),
                        ft.Column(
                            controls=order_cards,
                            scroll=ft.ScrollMode.AUTO,
                            expand=True,
                            spacing=5
                        ),
                    ],
                    spacing=10,
                    expand=True,
                ),
                padding=10,
                expand=True
            )
        
        self.main_content.content = content
        page.update()
    
    def show_profile_view(self, page: ft.Page):
        """Display profile view"""
        self.current_view = "profile"
        
        cycle_length_field = ft.TextField(
            label="Cycle Length (days)",
            value=str(self.settings.cycle_length),
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        period_length_field = ft.TextField(
            label="Period Length (days)",
            value=str(self.settings.period_length),
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        last_period_field = ft.TextField(
            label="Last Period Date (YYYY-MM-DD)",
            value=self.settings.last_period_date.strftime('%Y-%m-%d') if self.settings.last_period_date else ""
        )
        
        def save_settings(e):
            try:
                cycle_length = int(cycle_length_field.value)
                period_length = int(period_length_field.value)
                last_period_date = last_period_field.value
                
                self.db.save_settings(cycle_length, period_length, last_period_date)
                self.settings = self._load_settings()
                
                page.snack_bar = ft.SnackBar(ft.Text("Settings saved successfully!"))
                page.snack_bar.open = True
                page.update()
                
                self.show_home_view(page)
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"))
                page.snack_bar.open = True
                page.update()
        
        content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Profile Settings", size=24, weight="bold", color="#D946A6", offset=ft.transform.Offset(0.02, 0)),
                    ft.Divider(height=20),
                    ft.Text("Cycle Information", size=14, weight="bold", color="#1F2937"),
                    cycle_length_field,
                    period_length_field,
                    last_period_field,
                    ft.ElevatedButton(
                        "Save Settings",
                        icon=ft.icons.SAVE,
                        color="white",
                        bgcolor="#EC4899",
                        expand=True,
                        on_click=save_settings
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=10,
                expand=True,
            ),
            padding=10,
            expand=True
        )
        
        self.main_content.content = content
        page.update()
    
    def show_log_period_dialog(self, page: ft.Page):
        """Show dialog to log period"""
        date_field = ft.TextField(
            label="Date (YYYY-MM-DD)",
            value=datetime.now().strftime('%Y-%m-%d')
        )
        
        flow_dropdown = ft.Dropdown(
            label="Flow Intensity",
            options=[
                ft.dropdown.Option("light"),
                ft.dropdown.Option("medium"),
                ft.dropdown.Option("heavy"),
            ],
            value="medium"
        )
        
        notes_field = ft.TextField(
            label="Notes",
            multiline=True,
            min_lines=2
        )
        
        def save_period(e):
            try:
                self.db.add_period_entry(
                    date_field.value,
                    flow_dropdown.value,
                    notes_field.value
                )
                
                page.snack_bar = ft.SnackBar(ft.Text("Period logged successfully!"))
                page.snack_bar.open = True
                page.update()
                
                dlg.open = False
                page.update()
                self.show_home_view(page)
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"))
                page.snack_bar.open = True
                page.update()
        
        dlg = ft.AlertDialog(
            title=ft.Text("Log Period"),
            content=ft.Column(
                controls=[date_field, flow_dropdown, notes_field],
                spacing=10
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: (setattr(dlg, 'open', False), page.update())),
                ft.TextButton("Save", on_click=save_period),
            ]
        )
        
        page.dialog = dlg
        dlg.open = True
        page.update()
    
    def show_add_symptom_dialog(self, page: ft.Page):
        """Show dialog to add symptom"""
        date_field = ft.TextField(
            label="Date (YYYY-MM-DD)",
            value=datetime.now().strftime('%Y-%m-%d')
        )
        
        symptom_dropdown = ft.Dropdown(
            label="Symptom Type",
            options=[
                ft.dropdown.Option("cramps"),
                ft.dropdown.Option("mood"),
                ft.dropdown.Option("energy"),
                ft.dropdown.Option("bloating"),
                ft.dropdown.Option("headache"),
                ft.dropdown.Option("nausea"),
                ft.dropdown.Option("back pain"),
                ft.dropdown.Option("other"),
            ],
            value="cramps"
        )
        
        intensity_slider = ft.Slider(
            min=1,
            max=5,
            divisions=4,
            value=3,
            label="Intensity: {value}"
        )
        
        notes_field = ft.TextField(
            label="Notes",
            multiline=True,
            min_lines=2
        )
        
        def save_symptom(e):
            try:
                self.db.add_symptom(
                    date_field.value,
                    symptom_dropdown.value,
                    int(intensity_slider.value),
                    notes_field.value
                )
                
                page.snack_bar = ft.SnackBar(ft.Text("Symptom logged successfully!"))
                page.snack_bar.open = True
                page.update()
                
                dlg.open = False
                page.update()
                self.show_home_view(page)
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"))
                page.snack_bar.open = True
                page.update()
        
        dlg = ft.AlertDialog(
            title=ft.Text("Add Symptom"),
            content=ft.Column(
                controls=[date_field, symptom_dropdown, intensity_slider, notes_field],
                spacing=10
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: (setattr(dlg, 'open', False), page.update())),
                ft.TextButton("Save", on_click=save_symptom),
            ]
        )
        
        page.dialog = dlg
        dlg.open = True
        page.update()
    
    def add_to_cart(self, page: ft.Page, product):
        """Add product to cart"""
        self.cart.add_item(product.id, product.name, product.price, 1)
        self.db.add_to_cart(product.id, product.name, product.price, 1)
        
        page.snack_bar = ft.SnackBar(ft.Text(f"{product.name} added to cart!"))
        page.snack_bar.open = True
        page.update()
    
    def show_cart_view(self, page: ft.Page):
        """Display shopping cart"""
        if self.cart.is_empty():
            content = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Shopping Cart", size=24, weight="bold", color="#EC4899", offset=ft.transform.Offset(0.02, 0)),
                        ft.Container(
                            content=ft.Text("Your cart is empty", size=16, color="#4B5563", text_align=ft.TextAlign.CENTER),
                            expand=True,
                            alignment=ft.alignment.center
                        ),
                    ],
                    spacing=10,
                    expand=True
                ),
                padding=10,
                expand=True
            )
        
        if not self.cart.is_empty():
            cart_items_ui = []
            for item in self.cart.items:
                item_card = ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Column(
                                            controls=[
                                                ft.Text(item.product_name, size=13, weight="bold", color="#1F2937"),
                                                ft.Text(f"${item.price:.2f} each", size=11, color="#4B5563"),
                                            ],
                                            expand=True
                                        ),
                                        ft.Text(f"${item.get_total():.2f}", size=14, weight="bold", color="#EC4899"),
                                    ]
                                ),
                                ft.Row(
                                    controls=[
                                        ft.IconButton(
                                            icon=ft.icons.REMOVE,
                                            icon_color="#A855F7",
                                            on_click=lambda e, pid=item.product_id: self.update_cart_quantity(page, pid, item.quantity - 1)
                                        ),
                                        ft.Text(f"Qty: {item.quantity}", size=12, color="#1F2937"),
                                        ft.IconButton(
                                            icon=ft.icons.ADD,
                                            icon_color="#A855F7",
                                            on_click=lambda e, pid=item.product_id: self.update_cart_quantity(page, pid, item.quantity + 1)
                                        ),
                                        ft.Spacer(),
                                        ft.IconButton(
                                            icon=ft.icons.DELETE,
                                            icon_color="#EF4444",
                                            on_click=lambda e, pid=item.product_id: self.remove_from_cart(page, pid)
                                        ),
                                    ]
                                ),
                            ],
                            spacing=8
                        ),
                        padding=12,
                    ),
                    margin=8
                )
                cart_items_ui.append(item_card)
            
            subtotal = self.cart.get_subtotal()
            shipping = self.cart.get_shipping_cost()
            tax = self.cart.get_tax()
            total = self.cart.get_total()
            
            summary_text = f"Subtotal: ${subtotal:.2f}\nShipping: ${shipping:.2f}\nTax (8%): ${tax:.2f}\n\nTotal: ${total:.2f}"
            
            summary_card = ft.Card(
                content=ft.Container(
                    content=ft.Text(summary_text, size=12, color="#1F2937", weight="bold"),
                    padding=15,
                ),
                margin=8
            )
            
            checkout_button = ft.ElevatedButton(
                "Proceed to Checkout",
                icon=ft.icons.PAYMENT,
                color="white",
                bgcolor="#EC4899",
                expand=True,
                on_click=lambda e: self.show_checkout_view(page)
            )
        else:
            content = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Shopping Cart", size=24, weight="bold", color="#EC4899", offset=ft.transform.Offset(0.02, 0)),
                        ft.Column(
                            controls=cart_items_ui,
                            scroll=ft.ScrollMode.AUTO,
                            expand=True,
                            spacing=5
                        ),
                        summary_card,
                        ft.Container(content=checkout_button, padding=ft.padding.only(left=10, right=10, bottom=10)),
                    ],
                    spacing=5,
                    expand=True
                ),
                padding=10,
                expand=True
            )    
        self.main_content.content = content
        page.update()
    
    def update_cart_quantity(self, page: ft.Page, product_id: str, quantity: int):
        """Update item quantity in cart"""
        self.cart.update_quantity(product_id, quantity)
        self.show_cart_view(page)
    
    def remove_from_cart(self, page: ft.Page, product_id: str):
        """Remove item from cart"""
        self.cart.remove_item(product_id)
        page.snack_bar = ft.SnackBar(ft.Text("Item removed from cart"))
        page.snack_bar.open = True
        self.show_cart_view(page)
    
    def show_checkout_view(self, page: ft.Page):
        """Display checkout form"""
        address_field = ft.TextField(
            label="Delivery Address",
            multiline=True,
            min_lines=3,
            value=""
        )
        
        phone_field = ft.TextField(
            label="Phone Number",
            value=""
        )
        
        card_field = ft.TextField(
            label="Card Number (16 digits)",
            value=""
        )
        
        expiry_field = ft.TextField(
            label="Expiry (MM/YY)",
            value=""
        )
        
        cvv_field = ft.TextField(
            label="CVV (3-4 digits)",
            value="",
            password=True
        )
        
        def process_payment(e):
            try:
                if not address_field.value.strip():
                    raise ValueError("Please enter delivery address")
                if not phone_field.value.strip():
                    raise ValueError("Please enter phone number")
                if not card_field.value.strip():
                    raise ValueError("Please enter card number")
                if not expiry_field.value.strip():
                    raise ValueError("Please enter expiry date")
                if not cvv_field.value.strip():
                    raise ValueError("Please enter CVV")
                
                order = OrderProcessor.create_order(
                    self.cart,
                    address_field.value,
                    phone_field.value
                )
                
                is_valid, message = OrderProcessor.validate_order(order)
                if not is_valid:
                    raise ValueError(message)
                
                success, payment_message = PaymentProcessor.process_payment(
                    order,
                    card_field.value,
                    expiry_field.value,
                    cvv_field.value
                )
                
                if success:
                    self.db.create_order(
                        order.order_number,
                        order.total_price,
                        order.delivery_address,
                        [{"product_name": item.product_name, "quantity": item.quantity, "price": item.price} for item in order.items]
                    )
                    
                    self.cart.clear()
                    
                    confirmation_text = f"Order Confirmed!\n\nOrder #: {order.order_number}\nTotal: ${order.total_price:.2f}\nDelivery: {order.delivery_address}\n\nThank you for your purchase!"
                    
                    dlg = ft.AlertDialog(
                        title=ft.Text("Order Confirmed"),
                        content=ft.Text(confirmation_text),
                        actions=[
                            ft.TextButton(
                                "Back to Shop",
                                on_click=lambda e: (setattr(dlg, 'open', False), page.update(), self.show_shop_view(page))
                            ),
                        ]
                    )
                    
                    page.dialog = dlg
                    dlg.open = True
                    page.update()
                else:
                    raise ValueError(payment_message)
                    
            except ValueError as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"))
                page.snack_bar.open = True
                page.update()
        
        total = self.cart.get_total()
        
        content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Checkout", size=24, weight="bold", color="#EC4899", offset=ft.transform.Offset(0.02, 0)),
                    ft.Divider(height=15),
                    ft.Text("Delivery Information", size=14, weight="bold", color="#1F2937"),
                    address_field,
                    phone_field,
                    ft.Divider(height=15),
                    ft.Text("Payment Information", size=14, weight="bold", color="#1F2937"),
                    card_field,
                    ft.Row(
                        controls=[expiry_field, cvv_field],
                        spacing=10
                    ),
                    ft.Divider(height=15),
                    ft.Card(
                        content=ft.Container(
                            content=ft.Text(f"Total Amount: ${total:.2f}", size=14, weight="bold", color="#EC4899"),
                            padding=15,
                        )
                    ),
                    ft.ElevatedButton(
                        "Complete Purchase",
                        icon=ft.icons.PAYMENT,
                        color="white",
                        bgcolor="#EC4899",
                        expand=True,
                        on_click=process_payment
                    ),
                    ft.TextButton(
                        "Back to Cart",
                        on_click=lambda e: self.show_cart_view(page)
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=10,
                expand=True,
            ),
            padding=10,
            expand=True
        )
        
        self.main_content.content = content
        page.update()
    
    def show_day_details(self, page: ft.Page, day: int, month: int, year: int):
        """Show details for a specific day"""
        date = datetime(year, month, day)
        date_str = date.strftime('%Y-%m-%d')
        
        symptoms = self.db.get_symptoms(date_str)
        
        symptoms_text = f"Symptoms for {date.strftime('%B %d, %Y')}:\n\n"
        if symptoms:
            for symptom in symptoms:
                symptoms_text += f"• {symptom['symptom_type'].capitalize()} - Intensity: {symptom['intensity']}/5\n"
        else:
            symptoms_text += "No symptoms logged"
        
        dlg = ft.AlertDialog(
            title=ft.Text(f"{date.strftime('%B %d, %Y')}"),
            content=ft.Text(symptoms_text),
            actions=[
                ft.TextButton("Close", on_click=lambda e: (setattr(dlg, 'open', False), page.update())),
            ]
        )
        
        page.dialog = dlg
        dlg.open = True
        page.update()

def main(page: ft.Page):
    """Main entry point"""
    # Set light theme with beautiful feminine colors
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#FFF5F8"  # Soft pink background
    
    app = CycleCareApp()
    app.build(page)

if __name__ == "__main__":
    ft.app(target=main)