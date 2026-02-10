import os
import MySQLdb
import MySQLdb.cursors
from flask import Flask
from flask_mysqldb import MySQL
from datetime import datetime

# 1. Setup the minimal Flask app to access your database
app = Flask(__name__)

# CONFIGURATION (Matches your app.py)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'rootpassword'
app.config['MYSQL_DB']  = 'pick_my_photo'

mysql = MySQL(app)

# Get the absolute path of the folder where THIS script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def auto_delete_expired_galleries():
    with app.app_context():
        print(f"[{datetime.now()}] Starting cleanup process...")
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # 2. Find galleries older than 40 days where subscription is expired
        query = """
            SELECT g.id 
            FROM galleries g
            JOIN studios s ON g.studio_id = s.id
            JOIN subscriptions sub ON s.user_id = sub.user_id
            WHERE g.created_at < NOW() - INTERVAL 40 DAY
            AND (sub.end_date < NOW() OR sub.status = 'expired')
        """
        cursor.execute(query)
        expired_galleries = cursor.fetchall()

        if not expired_galleries:
            print(f"[{datetime.now()}] No expired galleries found. Skipping.")
            return

        for gallery in expired_galleries:
            gallery_id = gallery['id']

            # 3. Fetch all photo and video paths for this gallery
            cursor.execute("SELECT image_path FROM gallery_images WHERE gallery_id = %s", (gallery_id,))
            images = cursor.fetchall()
            cursor.execute("SELECT video_path FROM gallery_videos WHERE gallery_id = %s", (gallery_id,))
            videos = cursor.fetchall()

            # 4. Physically delete files from the VPS disk
            for item in (images + videos):
                rel_path = item.get('image_path') or item.get('video_path')
                if rel_path:
                    # Construct absolute path: /var/www/project/static/uploads/file.jpg
                    full_path = os.path.join(BASE_DIR, rel_path.lstrip('/'))
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            print(f"Deleted file: {full_path}")
                        except Exception as e:
                            print(f"Error deleting file {full_path}: {e}")

            # 5. Delete rows from Database
            try:
                cursor.execute("DELETE FROM gallery_images WHERE gallery_id = %s", (gallery_id,))
                cursor.execute("DELETE FROM gallery_videos WHERE gallery_id = %s", (gallery_id,))
                cursor.execute("DELETE FROM galleries WHERE id = %s", (gallery_id,))
                print(f"Deleted Gallery ID {gallery_id} from database.")
            except Exception as e:
                print(f"Database error on Gallery {gallery_id}: {e}")

        mysql.connection.commit()
        cursor.close()
        print(f"[{datetime.now()}] Cleanup complete.")

if __name__ == "__main__":
    auto_delete_expired_galleries()