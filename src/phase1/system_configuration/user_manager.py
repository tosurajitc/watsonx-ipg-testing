import bcrypt
import psycopg2


class UserManager:
    def __init__(self):
        try:
            self.conn = psycopg2.connect("dbname=secure_db user=admin password=secure123")
            self.cursor = self.conn.cursor()
        except psycopg2.Error as e:
            print(f"Database connection failed: {e}")
            
    def execute_query(self, query, values=None):
        try:
            self.cursor.execute(query, values)
            self.conn.commit()
        except psycopg2.Error as e:
            print(f"Database query error: {e}")
    
    def fetch_one(self, query, values=None):
        try:
            self.cursor.execute(query, values)
            return self.cursor.fetchone()
        except psycopg2.Error as e:
            print(f"Error fetching data: {e}")
    
    def close(self):
        self.cursor.close()
        self.conn.close()
    
    def get_permissions(self, role):
        try:
            self.cursor.execute("SELECT * FROM permissions WHERE role=%s", (role,))
            result = self.cursor.fetchone()
        
            if result:
                return {"can_edit": result[1], "can_view": result[2], "can_delete": result[3]}
            return None
        except psycopg2.Error as e:
            print(f"Error fetching data: {e}")
    
    def hash_password(password):
        try:
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        except Exception as e:
            print(f"Password hashing error: {e}")

    def check_password(password, hashed):
        try:
            return bcrypt.checkpw(password.encode(), hashed.encode())
        except Exception as e:
            print(f"Password verification error: {e}")

