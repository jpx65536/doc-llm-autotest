# run.py
import os
from app import create_app

app = create_app()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(port=port, debug=True)