from flask import Flask, request, render_template
from process_city import City
from datetime import datetime

from database import db

app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    args = request.args
    city_name = args.get('city_name', 'wroclaw')
    if not city_name: city_name = 'wroclaw'
    pollutant = args.get('pollutant', 'co')
    if not pollutant: pollutant = 'co'
    date = args.get('date', '')
    if not date:
        date = datetime.today().strftime("%Y-%m-%d")
        pollutant = 'co'

    city = City(city_name, pollutant, int(datetime.strptime(date, "%Y-%m-%d").timestamp()))
    try:
        folium_map = city.get_chunked_city_map()
    except Exception as e:
        print(e)
        return render_template('error.html')

    if city.error:
        return render_template('error.html')

    folium_map.save('templates/maps/map.html')
    # return ""
    return render_template('index.html', city_name=city_name, pollutant=pollutant, date=date)


if __name__ == '__main__':
    app.run(debug=True)