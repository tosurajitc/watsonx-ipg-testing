import psycopg2
import pandas as pd
import redis
import json

class RuleEngine:
    def __init__(self):
        self.conn = psycopg2.connect("dbname=rules_db user=admin password=secure123")
        self.cursor = self.conn.cursor()
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

    def load_rules(self):
        cached_rules = self.redis_client.get("cached_rules")
        if cached_rules:
            return pd.DataFrame(json.loads(cached_rules))
        
        self.cursor.execute("SELECT * FROM rule_definitions")
        rules = self.cursor.fetchall()
        rules_df = pd.DataFrame(rules, columns=["id", "test_priority", "defect_severity", "module", "assigned_team"])
        
        self.redis_client.set("cached_rules", json.dumps(rules_df.to_dict()))
        return rules_df

    def evaluate_rule(self, criteria):
        rules_df = self.load_rules()
        matched_rules = rules_df
        for key, value in criteria.items():
            matched_rules = matched_rules[matched_rules[key] == value]
        
        return matched_rules["assigned_team"].values[0] if not matched_rules.empty else "No match found"