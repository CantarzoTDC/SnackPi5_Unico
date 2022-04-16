from flask import Flask, request, send_file
from flask_restplus import Resource, Api
import base64
import json
import requests
import pyqrcode

from PIL import Image
from io import BytesIO


# from gerencianet import Gerencianet as gn


class Server(object):
    def __init__(self):
        self.app = Flask(__name__)
        self.api = Api(self.app,
                       version='1.0',
                       title='API PIX Gerencianet',
                       description='API para gerar pagamentos dinamicos. ',
                       doc='/docs'
                       )

    def run(self):
        self.app.run(debug=True, )


server = Server()


class Constants:
    # Produção
    class Prod:
        URL_PROD = 'https://api-pix.gerencianet.com.br'
        CLIENT_ID_PROD = 'Client_Id_5e91a758a6a345267fbf4e94cf90fab049220997'
        CLIENT_SECRET_PROD = 'Client_Secret_3716c3493a46287e47617504a9c30b69e112a165'
        CERT_PROD = 'GNET/cert-prod.pem'

    # Homologação
    class Hom:
        URL_HOM = 'https://api-pix-h.gerencianet.com.br'
        CLIENT_ID_HOM = 'Client_Id_f03112c31caaef0e4f9f0da5860bfdcd685d4f4c'
        CLIENT_SECRET_HOM = 'Client_Secret_7ae05b173195f1a1c5207940e8df6ee06462859c'
        CERT_HOM = 'GNET/cert-hom.pem'


class Model:
    class PixModel():
        def __init__(self):
            self.headers = {
                'Authorization': f'Basic {self.get_token()}',
                'Content-Type': 'application/json'
            }

        def get_token(self, ):
            auth = base64.b64encode(
                f'{Constants.Hom.CLIENT_ID_HOM}:{Constants.Hom.CLIENT_SECRET_HOM}'.encode()).decode()

            headers = {
                'Authorization': f'Basic {auth}',
                'Content-Type': 'application/json'
            }

            payload = {"grant_Type": "client_credentials"}

            response = requests.post(
                f'{Constants.Hom.URL_HOM}/oauth/token',
                headers=headers,
                data=json.dumps(payload),
                cert=Constants.Hom.CERT_HOM)

            return json.loads(response.content)['access_token']

        def create_qrcode(self, location_id):
            """

            :rtype: object
            """
            response = requests.get(
                f'{Constants.Hom.URL_HOM}/v2/loc/{location_id}/qrcode',
                headers=self.headers,
                cert=Constants.Hom.CERT_HOM
            )

            json.loads(response.content)

        def create_order(self, txid, payload):
            response = requests.put(
                f'{Constants.Hom.URL_HOM}/v2/loc/{txid}/qrcode',
                data=json.dumps(payload),
                headers=self.headers,
                cert=Constants.Hom.CERT_HOM
            )

            if response.status_code == 201:
                return json.loads(response.content)

            return {}

        def qrcode_generator(self, location_id):
            qrcode = self.create_qrcode(location_id)

            data_qrcode = qrcode['qrcode']

            url = pyqrcode.QRCode(data_qrcode, error='H')
            url.png('qrcode.jpg', scale=10)
            im = Image.open('qrcode.jpg')
            im = im.convert('RGBA')
            img_io = BytesIO()
            im.save(img_io, 'PNG', quality=100)
            img_io.seek(0)

            return send_file(img_io, mimetype='image/jpeg', as_attachment=False, attachment_filename='image-qrcode.jpg')

        def create_charge(self, txid, payload):
            location_id = self.create_order(txid, payload).get('loc').get('id')
            qrcode = self.qrcode_generator(location_id)

            return qrcode


class Controller:
    api = server.api

    @api.route('/orders', methods=['POST'])
    class Pix(Resource):

        def post(self, ):
            payload = request.json
            txid = payload.pop('txid')

            pix_model = Model.PixModel()
            response = pix_model.create_charge(txid, payload)

            return response

    @api.route('/token', methods=['POST'])
    class Token(Resource):
        def post(self, ):
            pix_model = Model.PixModel()
            response = pix_model.get_token()

            return response


class main():
    if __name__ == '__main__':
        server.run()
