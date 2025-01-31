import os


class Config:
    def __init__(self):
        self.admin_ids = list(map(int, os.getenv("ADMIN_IDS").split(",")))