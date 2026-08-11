import hashlib, itertools, math, sqlite3, time
from datetime import datetime as _dt

DB_PATH = 'vilvam.db'
DIESEL_PRICE = 2.15

def get_connection():
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; return conn

def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

def get_truck_engine_capacity_liters(brand, model):
    brand = (brand or '').strip().lower()
    model = (model or '').strip().lower()
    if brand == 'hino':
        if '700' in model or 'heavy' in model:
            return 12.9
        if '500' in model:
            return 8.0
        if '300' in model or '2-ton' in model or 'light duty' in model:
            return 4.0
    if brand == 'scania':
        if 'p310' in model or 'heavy duty' in model:
            return 13.0
        return 9.0
    if brand == 'volvo':
        return 12.0
    if brand == 'isuzu':
        return 9.0
    if brand == 'toyota':
        return 2.8
    if brand == 'mitsubishi':
        return 3.0
    return 4.0


def get_truck_fuel_multiplier(brand, model):
    engine_liters = get_truck_engine_capacity_liters(brand, model)
    return 1.0 + max(0.0, engine_liters - 4.0) / 10.0


def ensure_column(c, table, column, definition):
    cols=[r[1] for r in c.execute(f'PRAGMA table_info({table})').fetchall()]
    if column not in cols: c.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')

def init_db():
    conn=get_connection(); c=conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stock_items(id INTEGER PRIMARY KEY AUTOINCREMENT,item_name TEXT UNIQUE,category TEXT,quantity INTEGER DEFAULT 0,unit TEXT DEFAULT 'units',daily_usage REAL DEFAULT 1,reorder_level INTEGER DEFAULT 100,supplier TEXT,operational_status TEXT DEFAULT 'Critical',last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS purchase_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,request_no TEXT UNIQUE,item_id INTEGER,requested_qty INTEGER,estimated_weight_kg REAL DEFAULT 0,reason TEXT,status TEXT DEFAULT 'Pending',created_by TEXT,reviewed_by TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,reviewed_at TIMESTAMP,completed_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY AUTOINCREMENT,customer_code TEXT UNIQUE,company_name TEXT,contact_person TEXT,phone TEXT,email TEXT,address TEXT,default_distance_km REAL DEFAULT 0,status TEXT DEFAULT 'Active',created_by TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS customer_sales_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,request_no TEXT UNIQUE,customer_id INTEGER,item_name TEXT,requested_qty REAL DEFAULT 0,unit_weight_kg REAL DEFAULT 1,unit_volume_m3 REAL DEFAULT 0.01,message TEXT,status TEXT DEFAULT 'Pending',created_by TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,assigned_delivery_id INTEGER,assigned_at TEXT,completed_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS trucks(id INTEGER PRIMARY KEY AUTOINCREMENT,plate_no TEXT UNIQUE,truck_type TEXT,capacity_kg REAL,capacity_m3 REAL DEFAULT 10,brand TEXT,model TEXT,year INTEGER,fuel_consumption_per_100km REAL DEFAULT 12,status TEXT DEFAULT 'Available',current_location TEXT DEFAULT 'Warehouse - KL',last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS delivery_schedules(id INTEGER PRIMARY KEY AUTOINCREMENT,schedule_no TEXT UNIQUE,internal_po TEXT UNIQUE,customer_id INTEGER,truck_id INTEGER,delivery_date TEXT,destination TEXT,item_name TEXT,quantity REAL DEFAULT 0,item_summary TEXT,driver_name TEXT,driver_phone TEXT,distance_km REAL DEFAULT 0,toll_cost REAL DEFAULT 0,fuel_litres REAL DEFAULT 0,fuel_cost REAL DEFAULT 0,avg_speed REAL DEFAULT 80.0,tank_capacity REAL DEFAULT 250.0,fuel_per_km REAL DEFAULT 0,tank_range_km REAL DEFAULT 0,load_weight_kg REAL DEFAULT 0,utilization_pct REAL DEFAULT 0,status TEXT DEFAULT 'Assigned',arrival_time TEXT,completed_time TEXT,verified_by TEXT,verification_status TEXT DEFAULT 'Pending',verification_note TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY AUTOINCREMENT,target_role TEXT,title TEXT,message TEXT,is_read INTEGER DEFAULT 0,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # migrate old databases
    for col,definition in [('operational_status',"TEXT DEFAULT 'Critical'")]: ensure_column(c,'stock_items',col,definition)
    delivery_cols=[('internal_po','TEXT'),('customer_id','INTEGER'),('item_name','TEXT'),('quantity','REAL DEFAULT 0'),('driver_name','TEXT'),('driver_phone','TEXT'),('distance_km','REAL DEFAULT 0'),('toll_cost','REAL DEFAULT 0'),('fuel_litres','REAL DEFAULT 0'),('fuel_cost','REAL DEFAULT 0'),('avg_speed','REAL DEFAULT 80.0'),('tank_capacity','REAL DEFAULT 250.0'),('fuel_per_km','REAL DEFAULT 0'),('tank_range_km','REAL DEFAULT 0'),('load_weight_kg','REAL DEFAULT 0'),('utilization_pct','REAL DEFAULT 0'),('arrival_time','TEXT'),('completed_time','TEXT'),('verified_by','TEXT'),('verification_status',"TEXT DEFAULT 'Pending'"),('verification_note','TEXT'),('estimated_arrival','TEXT'),('actual_quantity','REAL DEFAULT 0'),('driver_notes','TEXT'),('demo_started_at','REAL'),('demo_due_at','REAL'),('load_volume_m3','REAL DEFAULT 0'),('assigned_at','TEXT')]
    for col,definition in delivery_cols: ensure_column(c,'delivery_schedules',col,definition)
    seed(c)
    # Do not keep an operational truck status unless it has a real active delivery.
    # This prevents seeded/manual "On Route" trucks from showing route state with no
    # distance record behind the fuel/toll KPIs.
    c.execute("""UPDATE trucks
                 SET status='Available',current_location='Warehouse - KL',last_updated=CURRENT_TIMESTAMP
                 WHERE status IN ('Assigned','Loading','On Route','Arrived','Delivered')
                   AND NOT EXISTS (
                       SELECT 1 FROM delivery_schedules ds
                       WHERE ds.truck_id=trucks.id AND ds.status!='Completed'
                   )""")
    conn.commit(); conn.close()

def seed(c):
    users=[('Purchasing Staff','purchase@vilvam.com','purchase123','Purchasing Staff'),('Logistics Staff','logistics@vilvam.com','logistics123','Logistics Staff'),('Admin','admin@vilvam.com','admin123','Super Admin')]
    for n,e,p,r in users: c.execute('INSERT OR IGNORE INTO users(name,email,password,role) VALUES(?,?,?,?)',(n,e,hash_password(p),r))
    c.execute("UPDATE users SET name='Admin',role='Super Admin' WHERE lower(email)='admin@vilvam.com' OR role='Purchasing Super Admin'")
    stocks=[('Whole Milk','Dairy',180,'cartons',60,200,'Fresh Farm Sdn Bhd'),('Sourdough Bread','Bakery',85,'loaves',45,120,'Golden Bake Supply'),('Organic Blueberries','Fruits',40,'boxes',20,90,'Cameron Fresh Produce'),('Espresso Roast Coffee','Beverages',260,'packs',35,150,'Roast House MY'),('Cheddar Cheese','Dairy',70,'blocks',25,100,'Dairy Best Supplier')]
    for row in stocks: c.execute('INSERT OR IGNORE INTO stock_items(item_name,category,quantity,unit,daily_usage,reorder_level,supplier) VALUES(?,?,?,?,?,?,?)',row)
    customers=[('CUS-001','Econsave Klang','Mr. Hafiz','012-7711223','klang@econsave.demo','Jalan Kapar, Klang, Selangor',36),('CUS-002','Lotus’s Shah Alam','Ms. Aina','013-6622100','shahalam@lotus.demo','Seksyen 13, Shah Alam, Selangor',28),('CUS-003','Mydin Subang Jaya','Mr. Kumar','016-4429188','subang@mydin.demo','USJ 1, Subang Jaya, Selangor',42),('CUS-004','NSK Trade City Selayang','Ms. Lee','017-3318877','selayang@nsk.demo','Selayang, Selangor',58),('CUS-005','Giant Bandar Kinrara','Mr. Ravi','019-9002234','kinrara@giant.demo','Bandar Kinrara, Puchong, Selangor',45)]
    for row in customers: c.execute('INSERT OR IGNORE INTO customers(customer_code,company_name,contact_person,phone,email,address,default_distance_km,created_by) VALUES(?,?,?,?,?,?,?,?)',(*row,'System'))
    trucks=[
        ('VLV 1234','1-Ton Van',1000,4,'Toyota','Hiace',2022,10,'Available','Warehouse - KL'),
        ('VLV 3456','2-Ton Truck',2000,8,'Hino','300 Light Duty',2022,14,'Available','Warehouse - Shah Alam'),
        ('VLV 5678','5-Ton Truck',5000,20,'Hino','700',2021,18,'Available','Warehouse - KL'),
        ('VLV 7890','10-Ton Lorry',10000,35,'Scania','Heavy Duty',2023,25,'Maintenance','Workshop - KL'),
        ('JTA 1234','3-Ton Lorry',3000,16,'Mitsubishi','Fuso Canter',2021,12,'Available','Warehouse - KL'),
        ('VAB 2345','3-Ton Lorry',3000,16,'Mitsubishi','Fuso Canter',2021,12,'Available','Warehouse - KL'),
        ('JTT 3456','5-Ton Lorry',5000,24,'Hino','Series 500',2020,18,'Available','Warehouse - KL'),
        ('BQA 4567','5-Ton Lorry',5000,24,'Hino','Series 500',2020,18,'Available','Warehouse - Kuantan'),
        ('WXY 5678','10-Ton Lorry',10000,40,'Volvo','FM',2022,22,'Available','Warehouse - KL'),
        ('BPG 6789','10-Ton Lorry',10000,40,'Volvo','FM',2022,22,'Available','Warehouse - Shah Alam'),
        ('VFC 7890','Tanker Truck',8000,35,'Isuzu','Giga',2021,20,'Available','Depot - Seremban'),
        ('WUD 8901','3-Ton Lorry',3000,16,'Mitsubishi','Fuso Canter',2023,13,'Available','Warehouse - KL'),
        ('JRS 9012','5-Ton Lorry',5000,24,'Hino','Series 500',2021,18,'Available','Warehouse - KL'),
        ('BNT 0123','10-Ton Lorry',10000,40,'Scania','P310',2022,24,'Available','Warehouse - Nilai'),
        ('VGH 1123','3-Ton Lorry',3000,16,'Mitsubishi','Fuso Canter',2022,12,'Available','Warehouse - KL'),
        ('JLK 2234','5-Ton Lorry',5000,24,'Hino','Series 500',2021,18,'Available','Depot - Melaka'),
        ('BPR 3345','10-Ton Lorry',10000,40,'Volvo','FM',2023,24,'Maintenance','Workshop - KL'),
        ('VED 4456','Tanker Truck',8000,35,'Isuzu','Giga',2021,20,'Available','Depot - Ipoh'),
        ('WQA 5567','3-Ton Lorry',3000,16,'Mitsubishi','Fuso Canter',2022,12,'Available','Warehouse - KL'),
        ('JTB 6678','5-Ton Lorry',5000,24,'Hino','Series 500',2022,18,'Available','Depot - Kota Bharu'),
        ('BXD 7789','10-Ton Lorry',10000,40,'Scania','P310',2023,24,'Available','Warehouse - KL'),
        ('VFY 8890','Tanker Truck',8000,35,'Isuzu','Giga',2022,20,'Available','Depot - Kuching'),
        ('JUC 9901','3-Ton Lorry',3000,16,'Mitsubishi','Fuso Canter',2023,13,'Available','Warehouse - KL'),
        ('BKH 0012','5-Ton Lorry',5000,24,'Hino','Series 500',2023,18,'Available','Depot - JB'),
        ('VXA 1124','10-Ton Lorry',10000,40,'Volvo','FM',2023,24,'Maintenance','Workshop - Shah Alam'),
        ('JTJ 2235','3-Ton Lorry',3000,16,'Mitsubishi','Fuso Canter',2022,12,'Available','Warehouse - KL'),
        ('BPZ 3346','5-Ton Lorry',5000,24,'Hino','Series 500',2022,18,'Available','Warehouse - KL'),
        ('VDF 4457','Tanker Truck',8000,35,'Isuzu','Giga',2021,20,'Available','Depot - Penang'),
        ('WKL 5568','10-Ton Lorry',10000,40,'Scania','P310',2023,24,'Available','Warehouse - KL'),
        ('JMA 6679','3-Ton Lorry',3000,16,'Mitsubishi','Fuso Canter',2021,12,'Available','Warehouse - Shah Alam'),
        ('BYN 7780','5-Ton Lorry',5000,24,'Hino','Series 500',2022,18,'Available','Depot - Seremban'),
        ('VQE 8891','10-Ton Lorry',10000,40,'Volvo','FM',2023,24,'Available','Warehouse - KL'),
        ('JTD 9902','Tanker Truck',8000,35,'Isuzu','Giga',2022,20,'Available','Depot - Melaka'),
        ('BWF 1011','3-Ton Lorry',3000,16,'Mitsubishi','Fuso Canter',2023,13,'Available','Warehouse - KL'),
    ]
    for row in trucks: c.execute('INSERT OR IGNORE INTO trucks(plate_no,truck_type,capacity_kg,capacity_m3,brand,model,year,fuel_consumption_per_100km,status,current_location) VALUES(?,?,?,?,?,?,?,?,?,?)',row)
    # Keep existing demo database identities aligned with the supplied fleet photos.
    fleet_identity=[
        ('1-Ton Van',1000,4,'Toyota','Hiace','VLV 1234'),
        ('2-Ton Truck',2000,8,'Hino','300 Light Duty','VLV 3456'),
        ('5-Ton Truck',5000,20,'Hino','700','VLV 5678'),
        ('10-Ton Lorry',10000,35,'Scania','Heavy Duty','VLV 7890'),
    ]
    for truck_type,capacity_kg,capacity_m3,brand,model,plate in fleet_identity:
        c.execute('UPDATE trucks SET truck_type=?,capacity_kg=?,capacity_m3=?,brand=?,model=? WHERE plate_no=?',(truck_type,capacity_kg,capacity_m3,brand,model,plate))
    c.execute("UPDATE stock_items SET operational_status=CASE WHEN quantity<=reorder_level THEN 'Critical' ELSE 'Standby' END WHERE operational_status IS NULL OR operational_status='' ")

def verify_user(email,password):
    conn=get_connection(); r=conn.execute('SELECT name,role FROM users WHERE lower(email)=lower(?) AND password=?',(email,hash_password(password))).fetchone(); conn.close(); return tuple(r) if r else None

def get_all_users():
    conn=get_connection(); rows=conn.execute('SELECT id,name,email,role FROM users ORDER BY role,name').fetchall(); conn.close(); return [tuple(r) for r in rows]

def get_stock_items():
    conn=get_connection(); rows=conn.execute('''SELECT id,item_name,category,quantity,unit,daily_usage,reorder_level,supplier,ROUND(CASE WHEN daily_usage>0 THEN quantity/daily_usage ELSE 0 END,1),operational_status FROM stock_items ORDER BY item_name''').fetchall(); conn.close(); return [tuple(r) for r in rows]

def get_low_stock_items(): return [r for r in get_stock_items() if r[3]<=r[6]]

def update_stock_quantity(i,q):
    conn=get_connection(); item=conn.execute('SELECT item_name,reorder_level FROM stock_items WHERE id=?',(i,)).fetchone(); status='Critical' if int(q)<=item[1] else 'Standby'
    conn.execute('UPDATE stock_items SET quantity=?,operational_status=?,last_updated=CURRENT_TIMESTAMP WHERE id=?',(int(q),status,int(i))); conn.commit(); conn.close()
    if status=='Critical': notify('Purchasing Staff',f'Low stock: {item[0]}',f'{item[0]} dropped to {q} units, at or below the reorder level of {item[1]}.')

def create_purchase_request(item_id,qty,weight,reason,user):
    conn=get_connection(); n=conn.execute('SELECT COALESCE(MAX(id),0)+1 FROM purchase_requests').fetchone()[0]; no=f'PR-{n:04d}'; item=conn.execute('SELECT item_name FROM stock_items WHERE id=?',(item_id,)).fetchone()
    conn.execute("INSERT INTO purchase_requests(request_no,item_id,requested_qty,estimated_weight_kg,reason,status,created_by) VALUES(?,?,?,?,?,'Pending',?)",(no,int(item_id),int(qty),float(weight),reason,user)); conn.commit(); conn.close()
    notify('Logistics Staff',f'Pending approval: {no}',f'{no} requests {qty} units of {item[0] if item else "an item"} and is waiting for approval.')
    return no

def get_purchase_requests(status=None):
    conn=get_connection(); sql='''SELECT pr.id,pr.request_no,si.item_name,si.category,si.quantity,si.unit,pr.requested_qty,pr.estimated_weight_kg,pr.reason,pr.status,pr.created_by,pr.reviewed_by,pr.created_at,pr.reviewed_at,pr.completed_at,pr.item_id,si.operational_status FROM purchase_requests pr JOIN stock_items si ON pr.item_id=si.id'''; params=[]
    if status: sql+=' WHERE pr.status=?'; params=[status]
    sql+=' ORDER BY pr.id DESC'; rows=conn.execute(sql,params).fetchall(); conn.close(); return [tuple(r) for r in rows]

def update_purchase_request_status(i,status,user):
    conn=get_connection(); row=conn.execute('SELECT item_id FROM purchase_requests WHERE id=?',(i,)).fetchone(); conn.execute('UPDATE purchase_requests SET status=?,reviewed_by=?,reviewed_at=CURRENT_TIMESTAMP WHERE id=?',(status,user,int(i)))
    if row and status=='Approved': conn.execute("UPDATE stock_items SET operational_status='Stock Ready' WHERE id=?",(row[0],))
    conn.commit(); conn.close()

def complete_purchase_request(i):
    conn=get_connection(); row=conn.execute("SELECT item_id,requested_qty FROM purchase_requests WHERE id=? AND status='Approved'",(i,)).fetchone()
    if row:
        conn.execute("UPDATE stock_items SET quantity=quantity+?,operational_status='Standby',last_updated=CURRENT_TIMESTAMP WHERE id=?",(row[1],row[0])); conn.execute("UPDATE purchase_requests SET status='Completed',completed_at=CURRENT_TIMESTAMP WHERE id=?",(i,))
    conn.commit(); conn.close()

def get_customers():
    conn=get_connection(); rows=conn.execute("SELECT id,customer_code,company_name,contact_person,phone,email,address,default_distance_km,status FROM customers ORDER BY company_name").fetchall(); conn.close(); return [tuple(r) for r in rows]
def create_customer(code,name,contact,phone,email,address,distance,user):
    conn=get_connection(); conn.execute('INSERT INTO customers(customer_code,company_name,contact_person,phone,email,address,default_distance_km,created_by) VALUES(?,?,?,?,?,?,?,?)',(code,name,contact,phone,email,address,float(distance),user)); conn.commit(); conn.close()

def create_customer_sales_request(customer_id,item_name,qty,unit_weight_kg,unit_volume_m3,user,message=None):
    """Purchasing records a customer sales requirement for Logistics to fulfil."""
    conn=get_connection()
    customer=conn.execute('SELECT company_name FROM customers WHERE id=? AND status=\'Active\'',(int(customer_id),)).fetchone()
    if not customer:
        conn.close(); raise ValueError('The selected customer is not active.')
    n=conn.execute('SELECT COALESCE(MAX(id),0)+1 FROM customer_sales_requests').fetchone()[0]
    request_no=f'CSR-{n:04d}'
    qty=float(qty); weight=float(unit_weight_kg); volume=float(unit_volume_m3)
    text=(message or '').strip() or f"Customer {customer['company_name']} requested {qty:,.0f} unit(s) of {item_name}. Please arrange a suitable available truck for delivery."
    conn.execute('''INSERT INTO customer_sales_requests(request_no,customer_id,item_name,requested_qty,unit_weight_kg,unit_volume_m3,message,status,created_by)
                    VALUES(?,?,?,?,?,?,?,'Pending',?)''',(request_no,int(customer_id),str(item_name),qty,weight,volume,text,user))
    conn.commit(); conn.close()
    notify('Logistics Staff',f'New customer sales request: {request_no}',text)
    return request_no,text

def get_customer_sales_requests(status=None):
    conn=get_connection()
    sql='''SELECT r.id,r.request_no,r.customer_id,c.customer_code,c.company_name,c.contact_person,c.phone,
                  r.item_name,r.requested_qty,r.unit_weight_kg,r.unit_volume_m3,r.message,r.status,
                  r.created_by,r.created_at,r.assigned_delivery_id,r.assigned_at,r.completed_at
           FROM customer_sales_requests r JOIN customers c ON c.id=r.customer_id'''
    params=[]
    if status:
        sql+=' WHERE r.status=?'; params.append(status)
    sql+=' ORDER BY r.id DESC'
    rows=conn.execute(sql,params).fetchall(); conn.close(); return [dict(r) for r in rows]

def get_all_trucks():
    conn=get_connection(); rows=conn.execute('SELECT id,plate_no,truck_type,capacity_kg,capacity_m3,brand,model,year,fuel_consumption_per_100km,status,current_location FROM trucks ORDER BY plate_no').fetchall(); conn.close(); return [tuple(r) for r in rows]

def get_truck_assignment_map():
    """Return the current active order and original assignment time for each truck."""
    conn=get_connection()
    rows=conn.execute('''SELECT ds.truck_id,ds.schedule_no,ds.internal_po,
                                COALESCE(ds.assigned_at,ds.created_at) AS assigned_at,
                                ds.status
                         FROM delivery_schedules ds
                         JOIN (
                             SELECT truck_id,MAX(id) AS latest_id
                             FROM delivery_schedules
                             WHERE status!='Completed'
                             GROUP BY truck_id
                         ) x ON x.latest_id=ds.id
                         ORDER BY ds.id DESC''').fetchall()
    conn.close()
    return {int(r['truck_id']):dict(r) for r in rows}
def update_truck_status(i,status,location):
    conn=get_connection()
    truck_id=int(i)
    active=conn.execute("SELECT id FROM delivery_schedules WHERE truck_id=? AND status!='Completed' ORDER BY id DESC LIMIT 1",(truck_id,)).fetchone()
    workflow_statuses={'Assigned','Loading','On Route','Arrived','Delivered'}
    if status in workflow_statuses and active is None:
        conn.close()
        raise ValueError('This truck has no active delivery schedule. Create/assign the delivery first so route distance, fuel and toll KPIs can be calculated before setting it to '+status+'.')
    if status in {'Available','Maintenance'} and active is not None:
        conn.close()
        raise ValueError('This truck still has an active delivery. Complete/verify the delivery before changing the truck to '+status+'.')
    linked=None
    if active is not None and status in workflow_statuses:
        linked=_apply_delivery_status(conn,int(active['id']),status)
    conn.execute('UPDATE trucks SET status=?,current_location=?,last_updated=CURRENT_TIMESTAMP WHERE id=?',(status,location,truck_id))
    conn.commit(); conn.close()
    if linked is not None and status=='Delivered':
        notify('Logistics Staff',f'Verification needed: {linked[0]}',f'{linked[0]} has been marked Delivered and is waiting for management verification.')

def get_driver_information():
    """Return the latest known truck/status for each named driver."""
    conn=get_connection()
    rows=conn.execute('''SELECT ds.driver_name,ds.driver_phone,t.plate_no,ds.status,MAX(ds.delivery_date)
                         FROM delivery_schedules ds JOIN trucks t ON ds.truck_id=t.id
                         WHERE TRIM(COALESCE(ds.driver_name,''))!=''
                         GROUP BY ds.driver_name,ds.driver_phone,t.plate_no,ds.status
                         ORDER BY MAX(ds.delivery_date) DESC''').fetchall()
    conn.close(); return [tuple(r) for r in rows]

def recommend_truck(load_kg,load_m3=0):
    """Recommend the smallest Available truck that satisfies BOTH weight and volume."""
    required_kg=max(0.0,float(load_kg)); required_m3=max(0.0,float(load_m3))
    available=[r for r in get_all_trucks() if r[9]=='Available']
    fitting=sorted(
        [r for r in available if float(r[3])>=required_kg and float(r[4])>=required_m3],
        key=lambda r:(float(r[3])-required_kg)+(float(r[4])-required_m3)*250
    )
    if fitting:
        r=fitting[0]
        return {
            'available':True,
            'truck_id':r[0],
            'plate_no':r[1],
            'truck_type':r[2],
            'capacity_kg':r[3],
            'capacity_m3':r[4],
            'utilization_pct':round(required_kg/float(r[3])*100,1) if r[3] else 0,
            'volume_utilization_pct':round(required_m3/float(r[4])*100,1) if r[4] else 0,
            'reason':'Smallest currently available truck that safely fits both the order weight and volume.'
        }
    return {
        'available':False,
        'reason':'No currently Available company truck can satisfy both the required weight and volume. Use Smart Truck Allocation for a multi-truck plan, wait for a truck to return, or contact a subcontractor.'
    }

def recommend_available_fleet(load_kg,load_m3=0):
    """Choose a small available fleet without exponential search on large fleets."""
    required_kg=max(0.0,float(load_kg)); required_m3=max(0.0,float(load_m3))
    available=[r for r in get_all_trucks() if r[9]=='Available']
    if required_kg<=0 and required_m3<=0:
        return {
            'available':True,'trucks':[],'required_kg':0.0,'required_m3':0.0,
            'capacity_kg':0.0,'capacity_m3':0.0,'weight_utilization_pct':0,
            'volume_utilization_pct':0,'reason':'Forecast load is zero; no truck is required.'
        }
    total_kg=sum(float(r[3]) for r in available); total_m3=sum(float(r[4]) for r in available)
    if not available or total_kg<required_kg or total_m3<required_m3:
        return {
            'available':False,'trucks':[],'required_kg':required_kg,'required_m3':required_m3,
            'reason':'Available company trucks do not provide enough total weight and/or volume capacity. Consider supplemental trailer capacity or subcontractor support.'
        }
    candidates=[]
    # Exact search is fast for the normal 1-4 truck case used in day-to-day planning.
    exact_limit=min(4,len(available))
    for size in range(1,exact_limit+1):
        for combo in itertools.combinations(available,size):
            cap_kg=sum(float(r[3]) for r in combo); cap_m3=sum(float(r[4]) for r in combo)
            if cap_kg>=required_kg and cap_m3>=required_m3:
                # Prefer fewer trucks, then the least unused weight/volume capacity.
                score=(size,cap_kg-required_kg,cap_m3-required_m3)
                candidates.append((score,combo,cap_kg,cap_m3))
        if candidates: break
    if not candidates:
        # Larger plans use a bounded greedy selection instead of checking millions
        # or billions of combinations. Weight and volume are normalised so both
        # constraints influence the selected fleet.
        def contribution(r):
            weight_share=float(r[3])/required_kg if required_kg>0 else 0.0
            volume_share=float(r[4])/required_m3 if required_m3>0 else 0.0
            return weight_share+volume_share
        selected=[]; cap_kg=0.0; cap_m3=0.0
        for truck in sorted(available,key=contribution,reverse=True):
            selected.append(truck); cap_kg+=float(truck[3]); cap_m3+=float(truck[4])
            if cap_kg>=required_kg and cap_m3>=required_m3: break
        # Remove any unnecessary truck while preserving both constraints.
        for truck in list(reversed(selected)):
            if cap_kg-float(truck[3])>=required_kg and cap_m3-float(truck[4])>=required_m3:
                selected.remove(truck); cap_kg-=float(truck[3]); cap_m3-=float(truck[4])
        combo=tuple(selected)
        reason='Fast capacity plan selected for a large forecast load; the fleet satisfies both weight and volume requirements.'
    else:
        _,combo,cap_kg,cap_m3=min(candidates,key=lambda x:x[0])
        reason='Smallest available fleet that satisfies both weight and volume capacity.'
    return {
        'available':True,
        'trucks':[tuple(r) for r in combo],
        'required_kg':required_kg,
        'required_m3':required_m3,
        'capacity_kg':cap_kg,
        'capacity_m3':cap_m3,
        'weight_utilization_pct':round(required_kg/cap_kg*100,1) if cap_kg else 0,
        'volume_utilization_pct':round(required_m3/cap_m3*100,1) if cap_m3 else 0,
        'reason':reason
    }

def create_delivery_schedule(customer_id,truck_id,date,item_name,qty,summary,driver,phone,distance,toll,load,eta='',avg_speed=80.0,tank_capacity=250.0,load_m3=0,customer_request_id=None):
    conn=get_connection(); n=conn.execute('SELECT COALESCE(MAX(id),0)+1 FROM delivery_schedules').fetchone()[0]; sno=f'DS-{n:04d}'; po=f'IPO-{_dt.now().year}-{n:04d}'
    truck=conn.execute('SELECT capacity_kg,fuel_consumption_per_100km,brand,model,capacity_m3,status,plate_no FROM trucks WHERE id=?',(truck_id,)).fetchone(); cust=conn.execute('SELECT address FROM customers WHERE id=?',(customer_id,)).fetchone()
    if not truck:
        conn.close(); raise ValueError('Selected truck was not found.')
    if truck['status']!='Available':
        conn.close(); raise ValueError(f"Truck {truck['plate_no']} is no longer Available. Refresh and choose another truck.")
    if float(load)>float(truck['capacity_kg']) or float(load_m3)>float(truck['capacity_m3']):
        conn.close(); raise ValueError(f"Truck {truck['plate_no']} cannot carry this order. Required: {float(load):,.1f} kg / {float(load_m3):,.2f} m³; capacity: {float(truck['capacity_kg']):,.0f} kg / {float(truck['capacity_m3']):,.1f} m³.")
    distance_km = float(distance)
    base_l_per_100 = float(truck[1]) if truck else 12.0
    speed = float(avg_speed)
    if speed <= 70.0:
        speed_factor = 1.0
    else:
        speed_factor = 1.0 + min(0.9, (speed - 70.0) * 0.03)
    engine_liters = get_truck_engine_capacity_liters(truck[2], truck[3]) if truck else 4.0
    engine_factor = 1.0 + max(0.0, engine_liters - 4.0) * 0.06
    load_ratio = 1.0
    if truck and truck[0] and float(load) > 0:
        utilisation = float(load) / float(truck[0])
        if utilisation > 0.5:
            load_ratio = 1.0 + min(1.2, (utilisation - 0.5) * 1.6)
    distance_factor = 1.0
    if distance_km > 250.0:
        distance_factor = 1.0 + min(1.5, (distance_km - 250.0) / 525.0)
    fuel_per_km = round(base_l_per_100 / 100.0 * speed_factor * engine_factor * load_ratio * distance_factor, 3)
    fuel = round(distance_km * fuel_per_km, 2)
    range_km = round(float(tank_capacity) / fuel_per_km, 1) if fuel_per_km > 0 else 0.0
    fuel_cost = round(fuel * DIESEL_PRICE, 2)
    util = round(float(load) / float(truck[0]) * 100, 1) if truck and truck[0] else 0
    assigned_at=_dt.now().strftime('%Y-%m-%d %H:%M:%S')
    values=(sno,po,int(customer_id),int(truck_id),str(date),cust[0],item_name,float(qty),summary,driver,phone,distance_km,speed,float(tank_capacity),fuel_per_km,range_km,float(toll),fuel,fuel_cost,float(load),util,'Assigned',eta,float(load_m3),assigned_at)
    placeholders=','.join('?' for _ in values)
    cur=conn.execute(f'''INSERT INTO delivery_schedules(schedule_no,internal_po,customer_id,truck_id,delivery_date,destination,item_name,quantity,item_summary,driver_name,driver_phone,distance_km,avg_speed,tank_capacity,fuel_per_km,tank_range_km,toll_cost,fuel_litres,fuel_cost,load_weight_kg,utilization_pct,status,estimated_arrival,load_volume_m3,assigned_at) VALUES({placeholders})''',values)
    delivery_id=cur.lastrowid
    if customer_request_id is not None:
        req=conn.execute("SELECT status FROM customer_sales_requests WHERE id=?",(int(customer_request_id),)).fetchone()
        if not req or req['status']!='Pending':
            conn.rollback(); conn.close(); raise ValueError('This Purchasing customer request is no longer Pending. Refresh Delivery Schedule.')
        conn.execute("UPDATE customer_sales_requests SET status='Assigned',assigned_delivery_id=?,assigned_at=? WHERE id=?",(delivery_id,assigned_at,int(customer_request_id)))
    conn.execute("UPDATE trucks SET status='Assigned',current_location=?,last_updated=CURRENT_TIMESTAMP WHERE id=?",(cust[0],truck_id))
    conn.execute("UPDATE stock_items SET operational_status='Allocated',last_updated=CURRENT_TIMESTAMP WHERE lower(item_name)=lower(?)",(item_name,))
    conn.commit(); conn.close(); return sno,po

def get_delivery_schedules():
    conn=get_connection(); rows=conn.execute('''SELECT ds.id,ds.schedule_no,ds.internal_po,c.company_name,c.contact_person,c.phone,c.address,t.plate_no,t.truck_type,ds.delivery_date,ds.estimated_arrival,ds.item_name,ds.quantity,ds.actual_quantity,ds.item_summary,ds.driver_name,ds.driver_phone,ds.distance_km,ds.avg_speed,ds.tank_capacity,ds.fuel_per_km,ds.tank_range_km,ds.toll_cost,ds.fuel_litres,ds.fuel_cost,ds.load_weight_kg,ds.utilization_pct,ds.status,ds.arrival_time,ds.completed_time,ds.verified_by,ds.verification_status,ds.verification_note,ds.driver_notes,ds.created_at,ds.truck_id,ds.load_volume_m3,COALESCE(ds.assigned_at,ds.created_at) FROM delivery_schedules ds LEFT JOIN customers c ON ds.customer_id=c.id JOIN trucks t ON ds.truck_id=t.id ORDER BY ds.id DESC''').fetchall(); conn.close(); return [tuple(r) for r in rows]

def _apply_delivery_status(conn,i,status,driver_notes=None):
    extra=''; params=[status]
    if status=='Arrived': extra=',arrival_time=CURRENT_TIMESTAMP'
    if status=='Delivered': extra=',completed_time=CURRENT_TIMESTAMP,verification_status=\'Waiting Verification\''
    if driver_notes: extra+=',driver_notes=?'; params.append(driver_notes)
    params.append(int(i))
    conn.execute(f'UPDATE delivery_schedules SET status=?{extra} WHERE id=?',params)
    row=conn.execute('SELECT schedule_no,item_name,truck_id,destination FROM delivery_schedules WHERE id=?',(int(i),)).fetchone()
    if row:
        conn.execute('UPDATE trucks SET status=?,current_location=COALESCE(?,current_location),last_updated=CURRENT_TIMESTAMP WHERE id=?',(status,row['destination'],row['truck_id']))
    if status=='Delivered':
        if row: conn.execute("UPDATE stock_items SET operational_status='Delivered',last_updated=CURRENT_TIMESTAMP WHERE lower(item_name)=lower(?)",(row[1],))
    return row

def update_delivery_status(i,status,driver_notes=None):
    conn=get_connection()
    row=_apply_delivery_status(conn,i,status,driver_notes)
    conn.commit(); conn.close()
    if row and status=='Delivered': notify('Logistics Staff',f'Verification needed: {row[0]}',f'{row[0]} has been marked Delivered and is waiting for management verification.')

def start_demo_delivery_timer(i,seconds=60):
    """Start a viva-only countdown and move the linked delivery/truck On Route."""
    seconds=max(1,int(seconds)); conn=get_connection()
    row=conn.execute('SELECT id,schedule_no,status FROM delivery_schedules WHERE id=?',(int(i),)).fetchone()
    if not row:
        conn.close(); raise ValueError('Delivery record was not found.')
    if row['status'] in ('Delivered','Completed'):
        conn.close(); raise ValueError('This delivery is already delivered/completed and cannot start a demo trip.')
    other=conn.execute("SELECT schedule_no FROM delivery_schedules WHERE id!=? AND status='On Route' AND demo_due_at IS NOT NULL LIMIT 1",(int(i),)).fetchone()
    if other:
        conn.close(); raise ValueError(f'A demo timer is already running for {other[0]}. Finish that demo first.')
    started=time.time(); due=started+seconds
    _apply_delivery_status(conn,int(i),'On Route')
    conn.execute('UPDATE delivery_schedules SET demo_started_at=?,demo_due_at=? WHERE id=?',(started,due,int(i)))
    conn.commit(); conn.close(); return {'schedule_no':row['schedule_no'],'started_at':started,'due_at':due,'duration_seconds':seconds}

def get_demo_delivery_timer(i):
    conn=get_connection(); row=conn.execute('SELECT id,schedule_no,status,demo_started_at,demo_due_at FROM delivery_schedules WHERE id=?',(int(i),)).fetchone(); conn.close()
    return dict(row) if row else None

def complete_demo_delivery_if_due(i,now_ts=None):
    """Auto-deliver a timed viva route once its countdown reaches zero."""
    now_ts=time.time() if now_ts is None else float(now_ts); conn=get_connection()
    row=conn.execute('SELECT id,schedule_no,status,demo_due_at FROM delivery_schedules WHERE id=?',(int(i),)).fetchone()
    if not row or row['status']!='On Route' or row['demo_due_at'] is None or now_ts<float(row['demo_due_at']):
        conn.close(); return False
    linked=_apply_delivery_status(conn,int(i),'Delivered','Automatically marked Delivered after the 1-minute viva demo trip.')
    conn.execute('UPDATE delivery_schedules SET demo_due_at=NULL WHERE id=?',(int(i),))
    conn.commit(); conn.close()
    if linked: notify('Logistics Staff',f'Verification needed: {linked[0]}',f'{linked[0]} completed the 1-minute demo trip and is waiting for management verification.')
    return True

def verify_delivery(i,note,user,actual_qty=None):
    conn=get_connection(); row=conn.execute('SELECT truck_id,status,verification_status FROM delivery_schedules WHERE id=?',(i,)).fetchone()
    if not row:
        conn.close(); raise ValueError('Delivery record was not found.')
    if row['status']!='Delivered' or row['verification_status']!='Waiting Verification':
        conn.close(); raise ValueError('Only a Delivered record with Waiting Verification status can be verified.')
    if actual_qty is not None:
        conn.execute("UPDATE delivery_schedules SET status='Completed',verification_status='Verified',verified_by=?,verification_note=?,actual_quantity=?,completed_time=COALESCE(completed_time,CURRENT_TIMESTAMP) WHERE id=?",(user,note,float(actual_qty),int(i)))
    else:
        conn.execute("UPDATE delivery_schedules SET status='Completed',verification_status='Verified',verified_by=?,verification_note=?,completed_time=COALESCE(completed_time,CURRENT_TIMESTAMP) WHERE id=?",(user,note,int(i)))
    conn.execute("UPDATE trucks SET status='Available',current_location='Warehouse - KL' WHERE id=?",(row['truck_id'],))
    conn.execute("UPDATE customer_sales_requests SET status='Completed',completed_at=CURRENT_TIMESTAMP WHERE assigned_delivery_id=?",(int(i),))
    conn.commit(); conn.close()

def get_dashboard_summary():
    conn=get_connection(); one=lambda q: conn.execute(q).fetchone()[0] or 0
    active_route_filter = " WHERE status IN ('On Route','Arrived','Delivered')"
    travelled_filter = " WHERE status IN ('On Route','Arrived','Delivered','Completed')"
    d={'total_stock_items':one('SELECT COUNT(*) FROM stock_items'),'low_stock_items':one('SELECT COUNT(*) FROM stock_items WHERE quantity<=reorder_level'),'stock_ready':one("SELECT COUNT(*) FROM stock_items WHERE operational_status IN ('Stock Ready','Standby')"),'pending_requests':one("SELECT COUNT(*) FROM purchase_requests WHERE status='Pending'"),'available_trucks':one("SELECT COUNT(*) FROM trucks WHERE status='Available'"),'assigned_trucks':one("SELECT COUNT(*) FROM trucks WHERE status IN ('Assigned','Loading','On Route','Arrived','Delivered')"),'on_route_trucks':one("SELECT COUNT(*) FROM trucks WHERE status='On Route'"),'maintenance_trucks':one("SELECT COUNT(*) FROM trucks WHERE status='Maintenance'"),'pending_deliveries':one("SELECT COUNT(*) FROM delivery_schedules WHERE status NOT IN ('Completed')"),'total_insourced_deliveries':one('SELECT COUNT(*) FROM delivery_schedules'),'fuel_litres':one('SELECT ROUND(COALESCE(SUM(fuel_litres),0),2) FROM delivery_schedules'+active_route_filter),'fuel_cost':one('SELECT ROUND(COALESCE(SUM(fuel_cost),0),2) FROM delivery_schedules'+active_route_filter),'toll_cost':one('SELECT ROUND(COALESCE(SUM(toll_cost),0),2) FROM delivery_schedules'+active_route_filter),'fuel_litres_all_time':one('SELECT ROUND(COALESCE(SUM(fuel_litres),0),2) FROM delivery_schedules'+travelled_filter),'fuel_cost_all_time':one('SELECT ROUND(COALESCE(SUM(fuel_cost),0),2) FROM delivery_schedules'+travelled_filter),'toll_cost_all_time':one('SELECT ROUND(COALESCE(SUM(toll_cost),0),2) FROM delivery_schedules'+travelled_filter),'pending_verification':one("SELECT COUNT(*) FROM delivery_schedules WHERE verification_status='Waiting Verification'")}
    conn.close(); return d

def get_monthly_delivery_metrics():
    conn=get_connection(); rows=conn.execute("SELECT strftime('%Y-%m',delivery_date) month,COUNT(*) deliveries,ROUND(SUM(fuel_litres),2) fuel,ROUND(SUM(toll_cost),2) toll FROM delivery_schedules GROUP BY month ORDER BY month").fetchall(); conn.close(); return [tuple(r) for r in rows]

def get_report_summary():
    conn=get_connection()
    total=conn.execute('SELECT COUNT(*) FROM delivery_schedules').fetchone()[0] or 0
    completed=conn.execute("SELECT COUNT(*) FROM delivery_schedules WHERE status='Completed'").fetchone()[0] or 0
    distance=conn.execute('SELECT ROUND(COALESCE(SUM(distance_km),0),2) FROM delivery_schedules').fetchone()[0] or 0
    util=conn.execute('SELECT ROUND(COALESCE(AVG(utilization_pct),0),1) FROM delivery_schedules').fetchone()[0] or 0
    on_time=conn.execute("SELECT COUNT(*) FROM delivery_schedules WHERE status='Completed' AND completed_time IS NOT NULL AND date(completed_time)<=date(delivery_date)").fetchone()[0] or 0
    conn.close()
    performance=round(on_time/completed*100,1) if completed else 0
    return {'total_deliveries':total,'completed_deliveries':completed,'pending_deliveries':total-completed,'distance_km':distance,'avg_utilization':util,'delivery_performance':performance}

def get_request_forecast(history_days=30,forecast_days=7):
    conn=get_connection(); rows=conn.execute("SELECT requested_qty,estimated_weight_kg FROM purchase_requests WHERE status IN ('Approved','Completed') AND datetime(COALESCE(reviewed_at,created_at))>=datetime('now',?)",(f'-{history_days} days',)).fetchall(); caps=[r[0] for r in conn.execute("SELECT capacity_kg FROM trucks WHERE status!='Maintenance'").fetchall()]; conn.close(); tq=sum(r[0] or 0 for r in rows); tw=sum(r[1] or 0 for r in rows); avgq=tq/history_days if history_days else 0; avgw=tw/history_days if history_days else 0; fq=round(avgq*forecast_days); fw=round(avgw*forecast_days,2); cap=sum(caps)/len(caps) if caps else 0; need=math.ceil(fw/cap) if cap and fw else 0; return {'forecast_qty':fq,'forecast_weight':fw,'trucks_needed':need}

# ---------------- Viva demo reset and sample order history ----------------

def reset_demo_operational_data():
    """Clear temporary viva transactions while preserving users, trucks, customers and stock master data."""
    conn=get_connection()
    conn.execute('DELETE FROM delivery_schedules')
    conn.execute('DELETE FROM purchase_requests')
    conn.execute('DELETE FROM customer_sales_requests')
    conn.execute('DELETE FROM notifications')
    # Trucks are fixed master records. Reset only operational status/location for a clean demo.
    conn.execute("UPDATE trucks SET status='Available', current_location='Warehouse - KL', last_updated=CURRENT_TIMESTAMP WHERE status!='Maintenance'")
    conn.commit(); conn.close()

def generate_demo_sales_orders(products, days=30):
    """Generate historical orders and leave the latest delivery waiting for verification."""
    import random
    from datetime import date, timedelta
    clean_products=[]
    for item in products or []:
        if isinstance(item, dict):
            name=str(item.get('Product') or item.get('product') or 'Food Product')
            weight=float(item.get('Unit_Weight_kg') or item.get('unit_weight_kg') or 1.0)
        else:
            name=str(item); weight=1.0
        if name and name not in [x[0] for x in clean_products]:
            clean_products.append((name,max(weight,0.01)))
    if not clean_products:
        raise ValueError('No valid products were found in the active sales dataset.')
    conn=get_connection()
    customers=conn.execute("SELECT id,address,default_distance_km FROM customers WHERE status='Active' ORDER BY id").fetchall()
    trucks=conn.execute("SELECT id,capacity_kg,fuel_consumption_per_100km,brand,model FROM trucks WHERE status!='Maintenance' ORDER BY capacity_kg,id").fetchall()
    if not customers or not trucks:
        conn.close(); raise ValueError('Customer or truck master data is missing.')
    conn.execute('DELETE FROM delivery_schedules')
    conn.execute("UPDATE trucks SET status='Available',current_location='Warehouse - KL',last_updated=CURRENT_TIMESTAMP WHERE status!='Maintenance'")
    rng=random.Random(2914)
    order_no=1
    driver_names=['Amin','Kamarul','Rizal','Hafiz','Rahman','Muthu','Prakash','Siva','Vijay','Azman']
    today=date.today()
    for offset in range(days-1,-1,-1):
        delivery_day=today-timedelta(days=offset)
        order_count=1 + (1 if delivery_day.weekday() in (0,2,4,5) else 0)
        for j in range(order_count):
            product,unit_weight=clean_products[(offset+j)%len(clean_products)]
            qty=rng.randint(80,650)
            load=round(qty*unit_weight,2)
            suitable=[t for t in trucks if float(t['capacity_kg'] or 0)>=load]
            truck=suitable[0] if suitable else trucks[-1]
            customer=customers[(offset+j)%len(customers)]
            distance=round(float(customer['default_distance_km'] or rng.randint(20,180))*2,1)
            base=float(truck['fuel_consumption_per_100km'] or 12)/100.0
            load_ratio=min(load/max(float(truck['capacity_kg'] or 1),1),1.0)
            fuel_per_km=base*(0.88+0.32*load_ratio)*get_truck_fuel_multiplier(truck['brand'],truck['model'])
            fuel=round(distance*fuel_per_km,2)
            fuel_cost=round(fuel*DIESEL_PRICE,2)
            toll=round(distance*0.18,2)
            util=round(load/max(float(truck['capacity_kg'] or 1),1)*100,1)
            sno=f'DEMO-{delivery_day.strftime("%m%d")}-{order_no:03d}'
            po=f'SO-{delivery_day.strftime("%Y%m%d")}-{order_no:03d}'
            driver=driver_names[(order_no-1)%len(driver_names)]
            phone=f'01{2+(order_no%8)}-{3000000+order_no:07d}'
            completed=f'{delivery_day.isoformat()} 17:{(order_no*7)%60:02d}:00'
            sql="""INSERT INTO delivery_schedules(
                schedule_no,internal_po,customer_id,truck_id,delivery_date,destination,item_name,quantity,actual_quantity,item_summary,
                driver_name,driver_phone,distance_km,avg_speed,tank_capacity,fuel_per_km,tank_range_km,toll_cost,fuel_litres,fuel_cost,
                load_weight_kg,utilization_pct,status,completed_time,verified_by,verification_status,verification_note,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
            values=(sno,po,int(customer['id']),int(truck['id']),delivery_day.isoformat(),customer['address'],product,float(qty),float(qty),
             'Dummy sales order generated for viva fuel-cost demonstration',driver,phone,distance,80.0,250.0,round(fuel_per_km,3),
             round(250.0/fuel_per_km,1) if fuel_per_km else 0,toll,fuel,fuel_cost,load,util,'Completed',completed,'Demo Manager','Verified',
             'Automatically verified demo delivery',completed)
            conn.execute(sql,values)
            order_no+=1
    # Keep one current delivery in the real viva workflow so Delivery Verification
    # can be demonstrated instead of every generated order being pre-verified.
    latest=conn.execute('SELECT id,truck_id,destination FROM delivery_schedules ORDER BY id DESC LIMIT 1').fetchone()
    if latest:
        conn.execute("UPDATE delivery_schedules SET status='Delivered',verification_status='Waiting Verification',verified_by=NULL,verification_note=NULL WHERE id=?",(latest['id'],))
        conn.execute("UPDATE trucks SET status='Delivered',current_location=?,last_updated=CURRENT_TIMESTAMP WHERE id=?",(latest['destination'],latest['truck_id']))
    conn.commit()
    count=conn.execute('SELECT COUNT(*) FROM delivery_schedules').fetchone()[0]
    conn.close()
    return count

def get_fuel_cost_period_summary():
    conn=get_connection()
    day=conn.execute("SELECT COUNT(*),ROUND(COALESCE(SUM(fuel_litres),0),2),ROUND(COALESCE(SUM(fuel_cost),0),2) FROM delivery_schedules WHERE date(delivery_date)=date('now')").fetchone()
    week=conn.execute("SELECT COUNT(*),ROUND(COALESCE(SUM(fuel_litres),0),2),ROUND(COALESCE(SUM(fuel_cost),0),2) FROM delivery_schedules WHERE date(delivery_date)>=date('now','-6 days')").fetchone()
    month=conn.execute("SELECT COUNT(*),ROUND(COALESCE(SUM(fuel_litres),0),2),ROUND(COALESCE(SUM(fuel_cost),0),2) FROM delivery_schedules WHERE strftime('%Y-%m',delivery_date)=strftime('%Y-%m','now')").fetchone()
    daily=conn.execute("SELECT delivery_date,COUNT(*),ROUND(SUM(fuel_litres),2),ROUND(SUM(fuel_cost),2) FROM delivery_schedules GROUP BY delivery_date ORDER BY delivery_date").fetchall()
    conn.close()
    return {'day':tuple(day),'week':tuple(week),'month':tuple(month),'daily':[tuple(r) for r in daily]}

# ---------------- Notifications ----------------

def notify(role,title,message):
    """Create a notification for a role, skipping if an identical unread one already exists."""
    conn=get_connection()
    exists=conn.execute('SELECT id FROM notifications WHERE target_role=? AND title=? AND is_read=0',(role,title)).fetchone()
    if not exists: conn.execute('INSERT INTO notifications(target_role,title,message) VALUES(?,?,?)',(role,title,message)); conn.commit()
    conn.close()

def get_notifications(role,unread_only=False):
    conn=get_connection()
    if role=='Super Admin': sql='SELECT id,target_role,title,message,is_read,created_at FROM notifications'; params=[]
    else: sql="SELECT id,target_role,title,message,is_read,created_at FROM notifications WHERE target_role IN (?,'All')"; params=[role]
    if unread_only: sql+= (' AND' if 'WHERE' in sql else ' WHERE')+' is_read=0'
    sql+=' ORDER BY is_read ASC, created_at DESC'
    rows=conn.execute(sql,params).fetchall(); conn.close(); return [tuple(r) for r in rows]

def mark_notification_read(i):
    conn=get_connection(); conn.execute('UPDATE notifications SET is_read=1 WHERE id=?',(int(i),)); conn.commit(); conn.close()

def mark_all_notifications_read(role):
    conn=get_connection()
    if role=='Super Admin': conn.execute('UPDATE notifications SET is_read=1')
    else: conn.execute("UPDATE notifications SET is_read=1 WHERE target_role IN (?,'All')",(role,))
    conn.commit(); conn.close()

def get_unread_notification_count(role):
    conn=get_connection()
    if role=='Super Admin': n=conn.execute('SELECT COUNT(*) FROM notifications WHERE is_read=0').fetchone()[0]
    else: n=conn.execute("SELECT COUNT(*) FROM notifications WHERE target_role IN (?,'All') AND is_read=0",(role,)).fetchone()[0]
    conn.close(); return n or 0

def refresh_system_notifications(include_stock=True):
    """Scan current system state and raise/refresh notifications for known risk conditions."""
    conn=get_connection()
    if include_stock:
        for r in conn.execute("SELECT item_name,quantity,reorder_level,supplier FROM stock_items WHERE operational_status='Critical'").fetchall():
            notify('Purchasing Staff',f'Low stock: {r[0]}',f'{r[0]} is at {r[1]} units, at or below the reorder level of {r[2]}. Supplier: {r[3] or "Not assigned"}.')
    for r in conn.execute("SELECT request_no FROM purchase_requests WHERE status='Pending'").fetchall():
        notify('Logistics Staff',f'Pending approval: {r[0]}',f'{r[0]} is waiting for approval.')
    for r in conn.execute("SELECT schedule_no,truck_id FROM delivery_schedules WHERE verification_status='Waiting Verification'").fetchall():
        notify('Logistics Staff',f'Verification needed: {r[0]}',f'{r[0]} has been delivered and is waiting for management verification.')
    for r in conn.execute("SELECT schedule_no,delivery_date FROM delivery_schedules WHERE status NOT IN ('Completed') AND date(delivery_date)<date('now')").fetchall():
        notify('Logistics Staff',f'Late delivery: {r[0]}',f'{r[0]} was scheduled for {r[1]} and has not been completed yet.')
    conn.close()

init_db()
