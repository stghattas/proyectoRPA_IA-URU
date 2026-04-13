import pandas as pd
import matplotlib.pyplot as plt
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import os
import logging
from dotenv import load_dotenv

# Carga automáticamente las variables del archivo .env al sistema local
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VentasRPA:
    def __init__(self, excel_path):
        self.excel_path = excel_path
        self.df_ventas = None
        self.df_vehiculos = None
        self.metricas = {}
        self.report_image_path = 'dashboard_ventas.png'

    def extraer_datos(self):
        logging.info("Iniciando extracción de datos...")
        try:
            ventas_base = pd.read_excel(self.excel_path, sheet_name='VENTAS')
            nuevos_registros = pd.read_excel(self.excel_path, sheet_name='NUEVOS REGISTROS')
            self.df_vehiculos = pd.read_excel(self.excel_path, sheet_name='VEHICULOS')

            self.df_ventas = pd.concat([ventas_base, nuevos_registros], ignore_index=True)
            self.df_ventas.rename(columns={'ID_Vehículo': 'ID_Vehiculo'}, inplace=True)
            self.df_ventas = pd.merge(self.df_ventas, self.df_vehiculos, on='ID_Vehiculo', how='left')
            
            logging.info("Datos extraídos y consolidados exitosamente.")
        except Exception as e:
            logging.error(f"Error al leer el archivo Excel: {e}")
            raise

    def analizar_datos(self):
        logging.info("Iniciando análisis de datos...")
        try:
            df = self.df_ventas
            ventas_por_sede = df.groupby('Sede')['Precio Venta sin IGV'].sum().sort_values(ascending=False)
            top_5_modelos = df['MODELO'].value_counts().head(5)
            canales_ventas = df['Canal'].value_counts()
            segmento_ventas = df.groupby('Segmento')['Precio Venta sin IGV'].sum()
            clientes_unicos = df['Cliente'].nunique()
            total_operaciones = len(df)
            total_sin_igv = df['Precio Venta sin IGV'].sum()
            total_con_igv = df['Precio Venta Real'].sum()

            self.metricas = {
                'ventas_por_sede': ventas_por_sede,
                'top_5_modelos': top_5_modelos,
                'canales_ventas': canales_ventas,
                'segmento_ventas': segmento_ventas,
                'clientes_unicos': clientes_unicos,
                'total_operaciones': total_operaciones,
                'total_sin_igv': total_sin_igv,
                'total_con_igv': total_con_igv
            }
            logging.info("Análisis de datos completado.")
        except Exception as e:
            logging.error(f"Error en el análisis de datos: {e}")
            raise

    def generar_dashboard(self):
        logging.info("Generando visualizaciones...")
        try:
            plt.figure(figsize=(15, 10))
            plt.suptitle('Dashboard Resumen de Ventas', fontsize=18, fontweight='bold')

            plt.subplot(2, 2, 1)
            plt.bar(self.metricas['ventas_por_sede'].index, self.metricas['ventas_por_sede'].values, color='skyblue')
            plt.title('Ventas sin IGV por Sede')
            plt.xticks(rotation=45)
            plt.ylabel('Monto')

            plt.subplot(2, 2, 2)
            plt.barh(self.metricas['top_5_modelos'].index, self.metricas['top_5_modelos'].values, color='lightgreen')
            plt.title('Top 5 Modelos Más Vendidos')
            plt.gca().invert_yaxis()
            plt.xlabel('Cantidad')

            plt.subplot(2, 2, 3)
            plt.bar(self.metricas['canales_ventas'].index, self.metricas['canales_ventas'].values, color='coral')
            plt.title('Canales con Más Ventas')
            plt.xticks(rotation=45)
            plt.ylabel('Cantidad de Operaciones')

            plt.subplot(2, 2, 4)
            plt.pie(self.metricas['segmento_ventas'].values, labels=self.metricas['segmento_ventas'].index, 
                    autopct='%1.1f%%', startangle=90, colors=['gold', 'lightcoral', 'lightskyblue'])
            plt.title('Segmento de Clientes (Ventas sin IGV)')

            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            plt.savefig(self.report_image_path)
            plt.close()
            logging.info(f"Dashboard generado y guardado como {self.report_image_path}")
        except Exception as e:
            logging.error(f"Error al generar dashboard: {e}")
            raise

    def enviar_reporte_whatsapp(self):
        logging.info("Preparando envío por WhatsApp...")
        
        # Leemos las variables desde el entorno local (protegido por .env)
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        from_whatsapp = os.getenv('TWILIO_WHATSAPP_NUMBER')
        to_whatsapp = os.getenv('RECIPIENT_NUMBER')
        
        if not account_sid or not auth_token:
            logging.error("❌ Credenciales no encontradas. Verifica tu archivo .env")
            return

        # Obtenemos textos limpios para el reporte
        top_modelo_nombre = self.metricas['top_5_modelos'].index
        mejor_sede_nombre = self.metricas['ventas_por_sede'].index

        mensaje_texto = (
            f"📊 *REPORTE AUTOMATIZADO DE VENTAS* 📊\n\n"
            f"👤 Clientes Únicos: {self.metricas['clientes_unicos']:,}\n"
            f"🛒 Total de Ventas: {self.metricas['total_operaciones']:,}\n"
            f"💰 Ingresos (Sin IGV): S/ {self.metricas['total_sin_igv']:,.2f}\n"
            f"💵 Ingresos (Con IGV): S/ {self.metricas['total_con_igv']:,.2f}\n\n"
            f"🥇 *Top Modelo:* {top_modelo_nombre}\n"
            f"🏢 *Mejor Sede:* {mejor_sede_nombre}\n\n"
            f"🤖 _Enviado por tu Bot RPA en Python_"
        )


        url_dashboard = 'https://demo.twilio.com/owl.png'

        try:
            client = Client(account_sid, auth_token)
            
            message = client.messages.create(
                body=mensaje_texto,
                from_=from_whatsapp,
                to=to_whatsapp,
                media_url=[url_dashboard]
            )
            logging.info(f"✅ ¡ÉXITO! Reporte enviado a WhatsApp. Message SID: {message.sid}")
        except TwilioRestException as e:
            logging.error(f"❌ Error de Twilio al enviar mensaje: {e}")
        except Exception as e:
            logging.error(f"❌ Error desconocido al enviar WhatsApp: {e}")

    def ejecutar(self):
        self.extraer_datos()
        self.analizar_datos()
        self.generar_dashboard()
        self.enviar_reporte_whatsapp()
        logging.info("Proceso RPA finalizado con éxito.")

if __name__ == "__main__":
    ARCHIVO_EXCEL = "Ventas - Fundamentos.xlsx"
    rpa = VentasRPA(ARCHIVO_EXCEL)
    rpa.ejecutar()