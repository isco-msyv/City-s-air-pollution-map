import h3
import folium
from shapely.geometry import Polygon, Point
import pandas as pd
import shapely.wkt
import requests, json, hashlib
from models import CityGeometry, CityPolygonList, CityPollutionData


class City:
    pollution_data = dict()
    city_geojson = dict()
    pollygons_list = list()
    openweathermap_api_key = "a16f83be29b5b13d11cd70959214c0db"
    fail = False
    city_lat = 0
    city_lon = 0
    error = ""

    def __init__(self, city_name, pollutant, timestamp):
        self.name = city_name
        self.pollutant = pollutant
        self.timestamp = timestamp

    def load_geometry_info(self):
        CityPollutionData.query.filter_by(city="berlin").delete()
        CityPollutionData.query.filter_by(city="rome").delete()

        if self.name == "berlin":
            CityGeometry.query.filter_by(city=self.name).delete()

        city_geojson = CityGeometry.query.filter_by(city=self.name).first()

        if city_geojson:
            self.city_geojson = city_geojson.geometry
            self.city_lat = self.city_geojson.get('city_lat')
            self.city_lon = self.city_geojson.get('city_lon')
            return None

        osm_url = "https://nominatim.openstreetmap.org/search.php?q={}&polygon_geojson=1&format=json".format(self.name)
        geodata = requests.get(osm_url)
        geodata = geodata.json()

        if not geodata:
            self.error = "Can not find city"
            self.fail = True
            return None

        city_geodata = None
        for data in geodata:
            if 'geojson' in data.keys() and data['geojson']['coordinates']:
                city_geodata = data
                break

        if not city_geodata:
            self.error = "Can not find city"
            self.fail = True
            return None

        self.city_lat = city_geodata.get('lat')
        self.city_lon = city_geodata.get('lon')
        city_coordinates = city_geodata['geojson']['coordinates']

        self.city_geojson = {}
        self.city_geojson['type'] = 'Feature'
        self.city_geojson['city_lat'] = self.city_lat
        self.city_geojson['city_lon'] = self.city_lon
        self.city_geojson['geometry'] = {}
        self.city_geojson['geometry']['type'] = 'Polygon'
        self.city_geojson['geometry']['coordinates'] = city_coordinates

        CityGeometry.add(self.name, self.city_geojson)

    def load_pollygon_list(self):
        if self.name == "berlin":
            CityPolygonList.query.filter_by(city=self.name).delete()

        pollygons = CityPolygonList.query.filter_by(city=self.name).first()
        if pollygons:
            self.pollygons_list = pollygons.pollygons_list
            return None

        self.pollygons_list = []
        hasher = hashlib.md5()
        polyfill = h3.polyfill(self.city_geojson['geometry'], 6)

        for index in polyfill:
            for child in h3.h3_to_children(index):
                pollygon = {}
                pollygon['type'] = 'Feature'
                pollygon['geometry'] = {}
                pollygon['geometry']['type'] = 'Polygon'
                coordinates = list(h3.h3_to_geo_boundary(child, geo_json=True))
                pollygon['geometry']['coordinates'] = [[list(reversed(coordinate)) for coordinate in coordinates]]
                flat_list = [item for sublist in pollygon['geometry']['coordinates'] for item in sublist]
                polygin_str = " ".join(map(str, flat_list))
                hasher.update(polygin_str.encode('utf-8'))
                polygon_id = hasher.hexdigest()
                pollygon['PolygonId'] = polygon_id
                self.pollygons_list.append(pollygon)

    def load_pollution_data(self):
        self.pollution_data = {}

        if self.name == "berlin":
            CityPollutionData.query.filter_by(city=self.name).delete()

        pollution_data = CityPollutionData.query.filter_by(city=self.name).first()

        if pollution_data:
            self.pollution_data = pollution_data.pollution
            return None

        for polygon_data in self.pollygons_list:
            polygon = Polygon(polygon_data.get('geometry', {}).get('coordinates')[0])
            lon, lat = [cor for cor in list(polygon.centroid.coords)[0]]
            openweathermap_api_url = 'http://api.openweathermap.org/data/2.5/air_pollution/history?'
            openweathermap_api_url += f'lat={lat}&lon={lon}&start={self.timestamp}&end={self.timestamp}&appid={self.openweathermap_api_key}'
            data = requests.get(openweathermap_api_url)
            data = data.json()
            polution_data = data.get('list', [])[0].get('components')
            if not polution_data: continue
            polution_data['PolygonId'] = polygon_data.get('PolygonId')
            polygon_data['properties'] = polution_data

            for key, result in polution_data.items():
                if key not in self.pollution_data.keys(): self.pollution_data[key] = []
                self.pollution_data[key].append(result)

        CityPolygonList.add(self.name, self.pollygons_list)
        CityPollutionData.add(self.name, self.pollution_data, self.timestamp)

    def get_chunked_city_map(self):
        self.load_geometry_info()

        if self.error:
            return None

        self.load_pollygon_list()
        self.load_pollution_data()

        fmap = folium.Map(location=[self.city_lat, self.city_lon], tiles='cartodbpositron', zoom_start=10,
                          control_scale=True)
        pollution_data = df = pd.DataFrame(self.pollution_data)

        geojson = {
            'type': 'FeatureCollection',
            'features': self.pollygons_list
        }

        folium.Choropleth(
            geo_data=geojson,
            name='choropleth',
            key_on='feature.PolygonId',
            data=pollution_data,
            columns=['PolygonId', self.pollutant],
            fill_color='YlOrRd',
            fill_opacity=0.7,
            line_opacity=0.2,
            line_color='white',
            line_weight=0,
            highlight=True,
            smooth_factor=1.0,
            labels=True,
            sticky=False,
        ).add_to(fmap)

        folium.GeoJson(geojson,
                       name='Labels',
                       style_function=lambda x: {'weight': 1, 'color': 'white', 'fillColor': 'transparent',
                                                 'dashArray': '1 7'},
                       highlight_function=lambda x: {'weight': 1, 'color': 'white', 'fillColor': 'transparent',
                                                     'dashArray': '1 7'},
                       tooltip=folium.features.GeoJsonTooltip(
                           fields=['co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3'],
                           aliases=['co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3'],
                           labels=True, sticky=False)).add_to(fmap)

        return fmap
