from cryptography.fernet import Fernet
import psycopg2
import redis

class CredentialManager:
    def __init__(self):
        self.conn = psycopg2.connect("dbname=dbName user=user password=pwd")
        self.cursor = self.conn.cursor()
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.key = self.load_or_generate_key()
        self.cipher = Fernet(self.key)

    def load_or_generate_key(self):
        try:
            with open("key.key", "rb") as file:
                return file.read()
        except FileNotFoundError:
            key = Fernet.generate_key()
            with open("key.key", "wb") as file:
                file.write(key)
            return key

    def encrypt(self, plain_text):
        return self.cipher.encrypt(plain_text.encode()).decode()

    def decrypt(self, encrypted_text):
        return self.cipher.decrypt(encrypted_text.encode()).decode()

    def store_credentials(self, service, key, value):
        encrypted_value = self.encrypt(value)
        self.cursor.execute(
            "INSERT INTO credentials (service_name, config_key, encrypted_value) VALUES (%s, %s, %s)",
            (service, key, encrypted_value))
        self.conn.commit()
        self.redis_client.set(f"{service}:{key}", value)  # Cache the value
        print(f"Stored {service} credential securely.")

    def get_credentials(self, service, key):
        cached_value = self.redis_client.get(f"{service}:{key}")
        if cached_value:
            return cached_value  # Return from cache if available
        
        self.cursor.execute(
            "SELECT encrypted_value FROM credentials WHERE service_name=%s AND config_key=%s ORDER BY version DESC LIMIT 1",
            (service, key))
        result = self.cursor.fetchone()

        return self.decrypt(result[0]) if result else None
