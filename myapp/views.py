
# Import Django utilities for rendering templates, redirecting URLs, and handling HTTP responses.
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import JsonResponse

# Import authentication and authorization utilities to manage user sessions and access control.
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

# Import Django's messaging framework to provide feedback to users about actions (e.g., errors, success messages).
from django.contrib import messages


# Import email utilities to send emails from within Django.
from email.mime.text import MIMEText

# Import Django utilities to manage and manipulate template contexts and content safely.

# Import model and utility functions specific to the application for managing scans and validations.
from .models import Test
from .models import Persona
from .models import Categoria
from .models import Resultado
from myapp.validators import CustomPasswordValidator

# Import standard libraries and third-party libraries for additional functionalities.
import random
import smtplib
import logging

# Import Django's exception classes to handle specific exceptions such as validation errors.
from django.core.exceptions import ValidationError

# Import Django utility to fetch an object from the database or raise a 404 error if not found.
from django.shortcuts import get_object_or_404

from django.db.models import Count, Avg, F, ExpressionWrapper, fields
from django.db.models.functions import TruncMonth,TruncDay
from datetime import datetime, timedelta ,date
import csv
import requests
from django.db import connection


# Set up logging for error tracking and debugging.
logger = logging.getLogger(__name__)

# Views for the application

# View function to handle the home page request. Simply renders the 'home.html' template.
def home(request):
    # Simple view that renders the home page template
    return render(request, 'home.html')

# View function for the 'About' page, rendering the 'about.html' template.
def about(request):
    # Simple view that renders the about page template
    return render(request, 'about.html')

# This handels the registration process of users via form submissions.
def register(request):
    # This check if the form was submitted using POST method.
    if request.method == 'POST':
        # This Extract data from form fields submitted by the user.
        username = request.POST.get('username')
        password = request.POST.get('password1')
        email = request.POST.get('email')
        confirm_password = request.POST.get('password2')
      
        # This validate that all fields contain data.
        if not (username and password and email):
            messages.error(request, "Missing fields in the form.")
            return render(request, 'register.html')

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html')

        # Initialize and apply custom password validator
        password_validator = CustomPasswordValidator()
        try:
            # This will raise a ValidationError if the password fails any checks
            password_validator.validate(password)
        except ValidationError as e:
            messages.error(request, str(e))
            return render(request, 'register.html')

        # This attempt to create a new user and send a verification email.
        try:
            user = User.objects.create_user(username=username, email=email)
            user.set_password(password)  # This ensures that the password is correctly set & Securely set user's password.
            user.is_active = True  # The user will not be active until they verify their email.
            user.save() # This saves the user object in the database.
            login(request, user) 
            messages.success(request, 'Email verified successfully!')
            return redirect('homekpi')
        
        except Exception as e:
            messages.error(request, f'Registration failed: {e}')
            # If not a POST request, just show the registration form.
            return render(request, 'register.html')
    else:
        return render(request, 'register.html')


def KIP1(request):
     # Obtener las URLs más visitadas y contarlas
    valores = []
    campo=0
    conteos = 0
    if request.method == "POST":
        formula = request.POST.get("formula", "").replace(" ", "")  # Quita los espacios
        try:
            campo, valores, conteos = evaluar_formula(formula)
        except ValueError as e:
            # Maneja el error si el campo no existe
            messages.error(request, str(e))
            return redirect("kpi1")
     
      # Gráfico 2: Categoría más solicitada en Test
    categoria_counts = (
        Test.objects.values('categoria__nombre')
        .annotate(cantidad=Count('categoria'))
        .order_by('-cantidad')
    )
    categorias = [item['categoria__nombre'] for item in categoria_counts]
    cantidades = [item['cantidad'] for item in categoria_counts]

    result = Test.objects.values('nombre', 'fecha', 'calificacion')

    field_names = [field.name for field in Test._meta.fields]  # Obtiene los nombres de los campos


    # Calcular el índice de satisfacción promedio------------------------------------------------------
    indice_satisfaccion = Test.objects.aggregate(Avg('calificacion'))['calificacion__avg']
    
    # Redondear el resultado a 2 decimales si es necesario
    indice_satisfaccion = round(indice_satisfaccion, 2) if indice_satisfaccion else 0
    # Separar los datos para el gráfico
    
    # Contar la cantidad de cada calificación del 0 al 10
    calificaciones = Test.objects.values('calificacion').annotate(total=Count('calificacion')).order_by('calificacion')
    calificaciones_labels = [item['calificacion'] for item in calificaciones]
    calificaciones_totals = [item['total'] for item in calificaciones]
    
    indices_satisfaccion = calcular_indice_satisfaccion_por_genero()

    context = {
        'indice_satisfaccion_masculino': indices_satisfaccion['indice_satisfaccion_masculino'],
        'indice_satisfaccion_femenino': indices_satisfaccion['indice_satisfaccion_femenino']
    }
    context = {'tests': result, 
               'field_names': field_names,
               'categorias': categorias,
               'cantidades': cantidades,
               "campo": campo,
               "valores": valores,
               "conteos": conteos,
               'indice_satisfaccion': indice_satisfaccion,
                'calificaciones_labels': calificaciones_labels,
                'calificaciones_totals': calificaciones_totals,
                'indice_satisfaccion_masculino': indices_satisfaccion['indice_satisfaccion_masculino'],
              'indice_satisfaccion_femenino': indices_satisfaccion['indice_satisfaccion_femenino']
               }
    return render(request, 'kpi.html', context)

def evaluar_formula(formula):
    # Limpia los espacios de la fórmula ingresada
    campo = formula.strip()
    print(f"Campo solicitado: {campo}")  # Imprime el campo ingresado

    # Verifica si el campo existe en el modelo ScanResult
    if not hasattr(Test, campo):
        print(f"Error: El campo '{campo}' no existe en el modelo ScanResult.")
        raise ValueError(f"El campo '{campo}' no existe en el modelo ScanResult.")

    # Agrupa por el campo especificado y cuenta las ocurrencias de cada valor único
    resultados_contados = Test.objects.values(campo).annotate(conteo=Count(campo)).order_by(campo)

    # Extrae los datos para la gráfica: valores únicos y sus respectivos conteos
    valores = [resultado[campo] for resultado in resultados_contados]
    conteos = [resultado['conteo'] for resultado in resultados_contados]

    print(f"Valores únicos: {valores}")  # Imprime los valores únicos
    print(f"Conteos: {conteos}")  # Imprime los conteos

    # Retorna el nombre del campo, valores únicos y sus conteos
    return campo, valores, conteos

def calcular_indice_satisfaccion_por_genero():
    # Calcular el promedio de calificación para género masculino
    indice_satisfaccion_masculino = Test.objects.filter(cliente__sexo='masculino').aggregate(Avg('calificacion'))['calificacion__avg'] or 0
    # Calcular el promedio de calificación para género femenino
    indice_satisfaccion_femenino = Test.objects.filter(cliente__sexo='femenino').aggregate(Avg('calificacion'))['calificacion__avg'] or 0

    # Redondear a 2 decimales para mejor presentación
    indice_satisfaccion_masculino = round(indice_satisfaccion_masculino, 2)
    indice_satisfaccion_femenino = round(indice_satisfaccion_femenino, 2)

    return {
        'indice_satisfaccion_masculino': indice_satisfaccion_masculino,
        'indice_satisfaccion_femenino': indice_satisfaccion_femenino
    }

def KIP2(request):
    
    
    # Filtrar personas con rol 'personal' y contar la cantidad de tests que ha realizado cada una
    cantidad_tests = Persona.objects.filter(rol='personal').annotate(num_tests=Count('tests_como_personal'))
    
    # Calcular el total de tests realizados por todas las personas con rol 'personal'
    total_tests = sum([persona.num_tests for persona in cantidad_tests])
    
    # Crear una lista de diccionarios con el nombre y el porcentaje de tests realizados
    datos2 = [
        {
            'nombre': persona.nombre,
            'porcentaje_tests': (persona.num_tests / total_tests * 100) if total_tests > 0 else 0
        } for persona in cantidad_tests
    ]
    
   
    personas_personal = Persona.objects.filter(rol='personal')
    # Filtrar personas con rol 'personal' y contar la cantidad de tests que ha realizado cada una
    cantidad_tests = Persona.objects.filter(rol='personal').annotate(num_tests=Count('tests_como_personal'))
    # Crear una lista de diccionarios con el nombre y la cantidad de tests
    datos = [{'nombre': persona.nombre, 'cantidad_tests_realizados': persona.num_tests} for persona in cantidad_tests]
    
    
    
    
    
      # Calcular el tiempo promedio de ejecución para cada persona
    tiempo_promedio = Persona.objects.filter(rol='personal').annotate(
        tiempo_promedio=Avg(
            ExpressionWrapper(
                F('tests_como_personal__fecha_entrega') - F('tests_como_personal__fecha'),
                output_field=fields.DurationField()
            )
        )
    )

    # Crear una lista de diccionarios con el nombre y el tiempo promedio en días
    datos_tiempo_promedio = [
        {
            'nombre': persona.nombre,
            'tiempo_promedio_dias': persona.tiempo_promedio.days if persona.tiempo_promedio else 0
        } for persona in tiempo_promedio
    ]
    
    
    datos_promedio_calificacion = promediocalificacion()
    
    
    
    context = {
        'personals':personas_personal,
         'datos': datos,
         'datosporcentaje': datos2,
         'datos_tiempo_promedio': datos_tiempo_promedio,  # Tiempo promedio en días por test
        'datos_promedio_calificacion': datos_promedio_calificacion
    }
    print(f"Valores nombreporcentajess: {datos2}")  # Imprime los valores únicos
    
    return render(request, 'kpi2.html',context)
    

def promediocalificacion():
    promedio_calificacion = (
        Persona.objects.filter(rol='personal')
        .annotate(promedio_calificacion=Avg('tests_como_personal__calificacion'))
        .values('nombre', 'apellidos', 'promedio_calificacion')
    )

    # Preparar los datos para el contexto
    datos_promedio_calificacion = [
        {
            'nombre': f"{persona['nombre']} {persona['apellidos']}",
            'promedio_calificacion': persona['promedio_calificacion'] or 0  # Si es None, asigna 0
        }
        for persona in promedio_calificacion
    ]
    return datos_promedio_calificacion





def KIP3(request):
    
    
    datos = obtener_pruebas_mensuales()
    
    datostiempoespera =tiempodeespera()
    
    context={
          'datos_tiempo_espera': datostiempoespera,
          'datos': datos
    }
    
    return render(request, 'kpi3.html',context)
    

def tiempodeespera():
    # Calcular el tiempo de espera promedio por cada prueba
    tiempo_espera_por_prueba = (
        Test.objects.annotate(
            tiempo_espera=ExpressionWrapper(
                F('fecha_entrega') - F('fecha'),
                output_field=fields.DurationField()
            )
        )
        .values('nombre')  # Agrupar por nombre de la prueba
        .annotate(promedio_tiempo_espera=Avg('tiempo_espera'))  # Calcular el promedio de tiempo de espera
        .order_by('nombre')  # Ordenar alfabéticamente por nombre de la prueba
    )

    # Convertir el tiempo de espera promedio a días para cada prueba
    datos_tiempo_espera = [
        {
            'nombre': prueba['nombre'],
            'promedio_tiempo_espera_dias': prueba['promedio_tiempo_espera'].days if prueba['promedio_tiempo_espera'] else 0
        } for prueba in tiempo_espera_por_prueba
    ] 
    print(f"orderby pruebas times: {datos_tiempo_espera}")  # Imprime los conteos

    return datos_tiempo_espera
    
def obtener_pruebas_mensuales():
    # Año actual
    año_actual = datetime.now().year

    # Consulta para obtener la cantidad de pruebas por mes en el año actual
    pruebas_por_mes = (
        Test.objects.filter(fecha__year=año_actual)
        .annotate(mes=TruncMonth('fecha'))
        .values('mes')
        .annotate(cantidad=Count('id'))
        .order_by('mes')
    )

    # Crear un diccionario con la cantidad de pruebas por mes, iniciando con 0 para cada mes
    datos_por_mes = {mes: 0 for mes in range(1, 13)}
    for entry in pruebas_por_mes:
        mes = entry['mes'].month  # Extraer el número de mes
        datos_por_mes[mes] = entry['cantidad']  # Asignar la cantidad de pruebas al mes correspondiente

    # Preparar los datos para el gráfico
    datos = {
        'labels': ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'],
        'data': [datos_por_mes[mes] for mes in range(1, 13)]
    }

    return datos
    
    
    
def KIP4(request):
    datos2 = obtener_volumen_pruebas_semanales()
    
    datos = obtener_pruebas_semanales()
    
    datos_porcentaje = obtener_porcentaje_pruebas()
    
    datos_genero = obtener_volumen_pruebas_por_genero()
    
    context = {
        'datos': datos,
        'datos2': datos2,
         'datos_porcentaje': datos_porcentaje,
          'datos_genero': datos_genero
    }
    
    return render(request, 'kpi4.html', context)
    
def obtener_pruebas_semanales():
    hace_siete_dias = datetime.now() - timedelta(days=7)

    # Obtener la cantidad de pruebas por día en la última semana
    pruebas_por_dia = (
        Test.objects.filter(fecha__gte=hace_siete_dias)
        .annotate(dia=TruncDay('fecha'))
        .values('dia')
        .annotate(cantidad=Count('id'))
        .order_by('dia')
    )

    # Generar un diccionario con los días de la semana y la cantidad de pruebas
    dias_semana = [(hace_siete_dias + timedelta(days=i)).date() for i in range(7)]
    datos_por_dia = {dia: 0 for dia in dias_semana}  # Inicializar con 0 para cada día

    # Rellenar con la cantidad de pruebas de cada día de la consulta
    for entry in pruebas_por_dia:
        dia = entry['dia']  # Ya es un objeto date, no se necesita .date()
        datos_por_dia[dia] = entry['cantidad']  # Asignar la cantidad de pruebas

    # Preparar los datos para el gráfico
    datos = {
        'labels': [dia.strftime('%Y-%m-%d') for dia in dias_semana],
        'data': [datos_por_dia[dia] for dia in dias_semana]
    }

    return datos
    
def obtener_volumen_pruebas_semanales():
    # Fecha de hace 7 días desde hoy
    hace_siete_dias = datetime.now() - timedelta(days=7)

    # Obtener la cantidad de pruebas por día en la última semana, agrupado por nombre de prueba
    pruebas_por_dia_y_nombre = (
        Test.objects.filter(fecha__gte=hace_siete_dias)
        .annotate(dia=TruncDay('fecha'))
        .values('dia', 'nombre')
        .annotate(cantidad=Count('id'))
        .order_by('dia', 'nombre')
    )

    # Generar estructura para los datos del gráfico
    dias_semana = [(hace_siete_dias + timedelta(days=i)).date() for i in range(7)]
    nombres_pruebas = Test.objects.values_list('nombre', flat=True).distinct()

    # Crear un diccionario inicial con todos los nombres de prueba y 0 pruebas para cada día de la semana
    datos_por_prueba = {
        nombre: {dia: 0 for dia in dias_semana} for nombre in nombres_pruebas
    }

    # Rellenar el diccionario con los datos de la consulta
    for entry in pruebas_por_dia_y_nombre:
        dia = entry['dia']
        nombre = entry['nombre']
        datos_por_prueba[nombre][dia] = entry['cantidad']

    # Preparar los datos para el gráfico
    datos = {
        'labels': [dia.strftime('%Y-%m-%d') for dia in dias_semana],
        'datasets': [
            {
                'label': nombre,
                'data': [datos_por_prueba[nombre][dia] for dia in dias_semana],
                'fill': 'false'  # Sin relleno bajo las líneas
            }
            for nombre in nombres_pruebas
        ]
    }
    print(f"Valores pruebasSemanalesChartbytest: {datos}")  #
    return datos    

def obtener_porcentaje_pruebas():
    # Total de pruebas
    total_pruebas = Test.objects.count()

    # Contar el número de pruebas por tipo (nombre) y calcular el porcentaje
    pruebas_por_tipo = (
        Test.objects.values('nombre')
        .annotate(cantidad=Count('id'))
    )

    # Calcular el porcentaje para cada tipo de prueba
    datos = {
        'labels': [entry['nombre'] for entry in pruebas_por_tipo],
        'data': [
            (entry['cantidad'] / total_pruebas * 100) if total_pruebas > 0 else 0
            for entry in pruebas_por_tipo
        ]
    }
    return datos

def obtener_volumen_pruebas_por_genero():
    # Filtrar personas con rol de 'personal' y agrupar por género
    pruebas_por_genero = (
        Test.objects.filter(personal__rol='personal')
        .values('personal__sexo')  # Agrupar por el sexo del personal
        .annotate(cantidad=Count('id'))
    )

    # Crear un diccionario para los resultados
    datos = {'masculino': 0, 'femenino': 0}
    for entry in pruebas_por_genero:
        if entry['personal__sexo'].lower() == 'masculino':
            datos['masculino'] = entry['cantidad']
        elif entry['personal__sexo'].lower() == 'femenino':
            datos['femenino'] = entry['cantidad']

    return datos


def KIP5(request):
    datos_edad = obtener_tests_por_edad()
    
    datos_tests_por_edad = obtener_tests_por_edad_y_nombre()
    
    datos_tests_menos_usados = obtener_tests_menos_usados()
    
    datos_tests_mas_solicitados = obtener_tests_mas_solicitados()
    
    datos_genero = obtener_indice_genero()
    
    
    context = {
        'datos_edad': datos_edad,
        'datos_tests_por_edad': datos_tests_por_edad,
         'datos_tests_menos_usados': datos_tests_menos_usados,
         'datos_tests_mas_solicitados': datos_tests_mas_solicitados,
          'datos_genero': datos_genero
    }
    
    return render(request, 'kpi5.html',context)
    
def obtener_tests_por_edad():
    # Calcular la edad de cada cliente y contar la cantidad de tests por edad
    hoy = date.today()
    tests_por_edad = (
        Test.objects.filter(cliente__rol='cliente')
        .annotate(edad=(hoy.year - F('cliente__fnac__year')))
        .values('edad')
        .annotate(cantidad=Count('id'))
        .order_by('edad')
    )

    # Formatear los datos para el gráfico
    datos = {
        'labels': [str(entry['edad']) for entry in tests_por_edad],  # Edades
        'data': [entry['cantidad'] for entry in tests_por_edad]  # Cantidad de tests por edad
    }
    
    return datos   
    
def obtener_tests_por_edad_y_nombre():
    hoy = date.today()
    # Anotar la edad y contar la cantidad de cada tipo de test realizado por edad
    tests_por_edad_y_nombre = (
        Test.objects.filter(cliente__rol='cliente')
        .annotate(edad=hoy.year - F('cliente__fnac__year'))  # Calcula la edad del cliente
        .values('edad', 'nombre')  # Agrupar por edad y nombre del test
        .annotate(cantidad=Count('id'))
        .order_by('edad', 'nombre')
    )

    # Organizar los datos en el formato requerido para Chart.js
    edades = sorted(set(entry['edad'] for entry in tests_por_edad_y_nombre))  # Lista de edades únicas
    nombres_tests = sorted(set(entry['nombre'] for entry in tests_por_edad_y_nombre))  # Lista de nombres de tests únicos

    # Inicializar la estructura de datos para el gráfico
    datos = {nombre: [0] * len(edades) for nombre in nombres_tests}
    for entry in tests_por_edad_y_nombre:
        edad_index = edades.index(entry['edad'])
        datos[entry['nombre']][edad_index] = entry['cantidad']

    return {
        'labels': edades,
        'datasets': [{'label': nombre, 'data': datos[nombre]} for nombre in nombres_tests]
    }  
def obtener_tests_menos_usados():
    # Obtener los 5 tests menos usados (con menor cantidad de registros)
    tests_menos_usados = (
        Test.objects.values('nombre')
        .annotate(cantidad=Count('id'))
        .order_by('cantidad')[:5]
    )

    # Formatear los datos para enviarlos al gráfico
    datos = [{'label': entry['nombre'], 'y': entry['cantidad']} for entry in tests_menos_usados]
    return datos  


def obtener_tests_mas_solicitados():
    # Obtener los 5 tests más usados (con mayor cantidad de registros)
    tests_mas_solicitados = (
        Test.objects.values('nombre')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')[:5]  # Ordenar en orden descendente por cantidad
    )

    # Formatear los datos para enviarlos al gráfico
    datos = [{'label': entry['nombre'], 'y': entry['cantidad']} for entry in tests_mas_solicitados]
    return datos


def obtener_indice_genero():
    # Filtrar clientes y agrupar por sexo
    indice_genero = (
        Persona.objects.filter(rol="cliente")
        .filter(tests_como_cliente__isnull=False)  # Personas con tests realizados
        .values('sexo')  # Agrupar por sexo
        .annotate(total=Count('tests_como_cliente'))  # Contar los tests realizados
    )

    # Formatear los datos para Chart.js
    datos = {
        'labels': [entry['sexo'] for entry in indice_genero],  # 'Femenino', 'Masculino'
        'data': [entry['total'] for entry in indice_genero]  # Cantidad de tests
    }
    return datos

def KIP6(request):
    valores = []
    campo=0
    conteos = 0
    
    datos =[] 
    field_name = ""
    
    if request.method == "POST":
        formula = request.POST.get("formula", "").replace(" ", "")  # Quita los espacios
        try:
            campo, valores, conteos = evaluar_formula(formula)
        except ValueError as e:
            # Maneja el error si el campo no existe
            messages.error(request, str(e))
            return redirect("kpi6")

    
    result = Test.objects.all()
    field_names = [field.name for field in Test._meta.fields]  # Obtiene los nombres de los campos
    
    result = Persona.objects.all()
    field_namespersona = [field.name for field in Persona._meta.fields]  # Obtiene los nombres de los campos
    
    
    
    context = {
      'tests': result, 
       'field_names': field_names,
       'field_namespersona': field_namespersona,
        "campo": campo,
        "valores": valores,
        "conteos": conteos,
           'datos': datos, 
            'field_name': field_name
    }
    
    return render(request, 'kpiparametro.html', context)
  
def cargar(request):
    if request.method == "POST":
        # Obtener el archivo subido
        csv_file = request.FILES.get("csv_file")

        # Validar que el archivo tenga extensión .csv
        if not csv_file.name.endswith(".csv"):
            return HttpResponse("El archivo debe tener formato CSV.")

        # Leer y procesar el archivo CSV
        try:
            data = csv_file.read().decode("utf-8").splitlines()  # Decodificar el archivo
            reader = csv.DictReader(data)

            personas = []
            for row in reader:
                if "id" in row:
                    del row["id"]
                # Convertir la fecha al formato esperado por Django
                fecha_nac = datetime.strptime(row["fnac"], "%m/%d/%Y").date()
               
                # Normalizar el campo "telefono" (dejar solo los primeros 8 dígitos válidos)
                telefono = "".join(filter(str.isdigit, row["telefono"]))[:8]

                # Normalizar el campo "sexo"
                sexo = row["gender"].lower()
                if sexo == "male":
                    sexo = "masculino"
                elif sexo == "female":
                    sexo = "femenino"
                else:
                    sexo = "masculino"

                # Crear instancia de Persona
                persona = Persona(
                    nombre=row["nombre"],
                    apellidos=row["apellidos"],
                    sexo=sexo,
                    fnac=fecha_nac,
                    telefono=telefono,
                    rol=row["rol"],
                    #especialidad=row["especialidad"] if row["especialidad"] else None,
                    especialidad=None,
                )
                # Imprimir la instancia de Persona antes de agregarla
                print(f"Persona creada: {persona.__dict__}")
                personas.append(persona)

            # Guardar todas las personas en la base de datos
            #print( 'datos: ',personas)
            Persona.objects.bulk_create(personas)

            return HttpResponse("Datos cargados exitosamente.")
        except Exception as e:
            return HttpResponse(f"Error al procesar el archivo: {str(e)}")

    return render(request, "cargar.html")


def cargar_tests(request):
    if request.method == "POST":
        # Obtener el archivo subido
        csv_file = request.FILES.get("csv_file")

        # Validar que el archivo tenga extensión .csv
        if not csv_file.name.endswith(".csv"):
            return HttpResponse("El archivo debe tener formato CSV.")

        # Leer y procesar el archivo CSV
        try:
            data = csv_file.read().decode("utf-8").splitlines()  # Decodificar el archivo
            reader = csv.DictReader(data)
            # Cargar todas las categorías en caché
            categorias = {categoria.id: categoria for categoria in Categoria.objects.all()}
            personas_cache = {persona.id: persona for persona in Persona.objects.all()}
            
            
            tests = []
            resultados = []
            for row in reader:
                # Convertir la fecha al formato esperado por Django
                fecha_prueba = datetime.strptime(row["fecha"], "%m/%d/%Y").date()

                if "covid" in row["nombre"].lower():
                    dias_entrega = random.randint(1, 2)
                elif "paternidad" in row["nombre"].lower():
                    dias_entrega = random.randint(5, 10)
                elif "hemograma" in row["nombre"].lower():
                    dias_entrega = random.randint(1, 3)
                elif "influenza" in row["nombre"].lower():
                    dias_entrega = random.randint(2, 4)
                elif "alergia" in row["nombre"].lower():
                    dias_entrega = random.randint(3, 7)
                elif "electrocardiograma" in row["nombre"].lower():
                    dias_entrega = random.randint(1, 2)
                elif "anticuerpo" in row["nombre"].lower():
                    dias_entrega = random.randint(3, 5)
                elif "hepatitis" in row["nombre"].lower():
                    dias_entrega = random.randint(5, 10)
                else:
                    dias_entrega = random.randint(7, 14)  # Por defecto para pruebas no especificadas

                fecha_entrega = fecha_prueba + timedelta(days=dias_entrega)

                # Buscar la categoría y las personas relacionadas
                #categoria = Categoria.objects.get(id=row["categoria_id"])
                categoria_id = int(row["categoria_id"])
                categoria = categorias.get(categoria_id)
                
                '''
                try:
                    cliente = Persona.objects.get(id=row["cliente_id"])
                except Persona.DoesNotExist:
                    cliente_id = random.randint(1000, 3000)
                    cliente = Persona(id=cliente_id, nombre=f"Cliente-{cliente_id}")  # Creando un cliente temporal

                # Obtener el personal
                try:
                    personal = Persona.objects.get(id=row["personal_id"])
                except Persona.DoesNotExist:
                    personal_id = random.randint(1000, 2000)
                    personal = Persona(id=personal_id, nombre=f"Personal-{personal_id}") 
                '''
                 # Obtener cliente desde la caché o crear temporalmente con un ID aleatorio
                cliente_id = int(row["cliente_id"])
                try:
                    cliente = personas_cache[cliente_id]
                except KeyError:
                    cliente_id = random.randint(1000, 3000)
                    cliente = Persona(id=cliente_id, nombre=f"Cliente-{cliente_id}")  # Crear cliente temporal
                    personas_cache[cliente_id] = cliente  # Agregar al caché temporalmente

                # Obtener personal desde la caché o crear temporalmente con un ID aleatorio
                personal_id = int(row["personal_id"])
                try:
                    personal = personas_cache[personal_id]
                except KeyError:
                    personal_id = random.randint(1000, 2000)
                    personal = Persona(id=personal_id, nombre=f"Personal-{personal_id}")  # Crear personal temporal
                    personas_cache[personal_id] = personal  # Agregar al caché temporalmente
                
                
                # Crear la instancia del Test
                test = Test(
                    nombre=row["nombre"],
                    fecha=fecha_prueba,
                    fecha_entrega=fecha_entrega,
                    estado=row["estado"],
                    observaciones=row["observaciones"] if row["observaciones"] != "N/a" else None,
                    calificacion=int(row["calificacion"]),
                    categoria=categoria,
                    cliente=cliente,
                    personal=personal,
                )
                # Imprimir datos del test para depuración
                #observaciones=row["observaciones"] if row["observaciones"] != "N/a" else None,
                # Manejar el campo 'observaciones' con un valor predeterminado
                #para crear los resultados, se toman el nombre y se generan resutlados leatorios por codigo
                
                 # Generar el resultado del test
                resultado_text, interpretacion, detalles = generar_resultado(test.nombre)

                # Crear la instancia de Resultado
                resultado = Resultado(
                    test=test,
                    resultado=resultado_text,
                    fecha=fecha_entrega,
                    observaciones="N/a",
                    interpretacion=interpretacion,
                    detalles=detalles,
                    url_imagen_path=None,
                )
                resultados.append(resultado)
                
                
               

                tests.append(test)
                print(f"Resultado creado: {resultado.__dict__}")
                

            # Guardar todos los tests en la base de datos
            Test.objects.bulk_create(tests)
            Resultado.objects.bulk_create(resultados)

            return HttpResponse("Datos de los tests cargados exitosamente.")
        except Exception as e:
            return HttpResponse(f"Error al procesar el archivo: {str(e)}")

    return render(request, "cargar_tests.html")

# Función para generar el resultado del test
def generar_resultado(nombre_test):
    nombre_test = nombre_test.lower()

    if "covid" in nombre_test:
        resultado = random.choice(["Negativo", "Positivo"])
        interpretacion = "Infección activa" if resultado == "Positivo" else "No se detectó el virus"
        detalles = "Prueba PCR realizada correctamente."
    elif "paternidad" in nombre_test:
        resultado = random.choice(["Inclusión", "Exclusión"])
        interpretacion = "Coincidencia de marcadores genéticos" if resultado == "Inclusión" else "No hay relación biológica"
        detalles = "Prueba de ADN realizada con precisión."
    elif "hemograma" in nombre_test:
        resultado = "Normal" if random.random() > 0.2 else "Anormal"
        interpretacion = "Valores dentro de los rangos esperados" if resultado == "Normal" else "Anemia detectada"
        detalles = "Conteo completo de células sanguíneas."
    elif "influenza" in nombre_test:
        resultado = random.choice(["Negativo", "Positivo"])
        interpretacion = "Infección viral activa" if resultado == "Positivo" else "No se detectó el virus"
        detalles = "Prueba rápida de influenza."
    elif "alergia" in nombre_test:
        resultado = random.choice(["Sin alergias", "Alergias detectadas"])
        interpretacion = "Reacción alérgica" if resultado == "Alergias detectadas" else "Sin reacciones"
        detalles = "Panel de alérgenos completado."
    elif "electrocardiograma" in nombre_test:
        resultado = random.choice(["Normal", "Anormal"])
        interpretacion = "Ritmo cardíaco regular" if resultado == "Normal" else "Arritmia detectada"
        detalles = "ECG realizado sin complicaciones."
    elif "anticuerpo" in nombre_test:
        resultado = random.choice(["Positivo", "Negativo"])
        interpretacion = "Presencia de anticuerpos" if resultado == "Positivo" else "No se detectaron anticuerpos"
        detalles = "Prueba serológica completada."
    elif "hepatitis" in nombre_test:
        resultado = random.choice(["Negativo", "Positivo"])
        interpretacion = "Infección detectada" if resultado == "Positivo" else "No se detectó infección"
        detalles = "Análisis para hepatitis realizado."
    else:
        resultado = "Indeterminado"
        interpretacion = "No se pudo interpretar el resultado"
        detalles = "Datos insuficientes para el análisis."

    return resultado, interpretacion, detalles




def realizar_consulta(request):
    
    
    valores = []
    campo=0
    conteos = 0
    result = Test.objects.all()
    field_names = [field.name for field in Test._meta.fields]  # Obtiene los nombres de los campos
    result = Persona.objects.all()
    field_namespersona = [field.name for field in Persona._meta.fields]  # Obtiene los nombres de los campos
  
    
    try:
        # Obtener parámetros de la consulta
        field_name = request.GET.get('field_name')
        order = request.GET.get('order', 'asc')
        operation = request.GET.get('operation')

        # Validar los datos
        if not field_name or operation not in ['sum', 'avg']:
            raise ValueError('Parámetros inválidos')

        # Realizar la consulta en función de la operación
        if operation == 'sum':
            queryset = (
                Persona.objects.values(field_name)
                .annotate(total=Count(field_name))
                .order_by(f"{'' if order == 'asc' else '-'}total")
            )
        elif operation == 'avg':
            queryset = (
                Persona.objects.values(field_name)
                .annotate(total=Avg(field_name))
                .order_by(f"{'' if order == 'asc' else '-'}total")
            )
        else:
            queryset = []

        # Preparar datos para la gráfica
        datos = {
            'labels': [entry[field_name] for entry in queryset],
            'data': [entry['total'] for entry in queryset],
        }

    except Exception as e:
        # Manejar errores y pasar el mensaje al contexto
        error_message = str(e)
        datos =[] 
        
    
    
    
    context = {
        'tests': result, 
        'field_names': field_names,
        'field_namespersona': field_namespersona,
            "campo": campo,
            "valores": valores,
            "conteos": conteos,
            'datos': datos, 
            'field_name': field_name
        }
    return render(request, 'kpiparametro.html', context)


def KPIhome(request):
    return render(request, 'homekpi.html')


STATIC_DATABASE_SCHEMA = """
    Tabla: myapp_persona
      - nombre (CharField)
      - apellidos (CharField)
      - sexo (CharField)
      - fnac (DateField)
      - telefono (CharField)
      - rol (CharField)
      - especialidad (CharField)

    Tabla: myapp_test
      - nombre (CharField)
      - fecha (DateField)
      - fecha_entrega (DateField)
      - estado (CharField)
      - observaciones (TextField)
      - calificacion (IntegerField)
      - categoria (ForeignKey)
      - cliente (ForeignKey)
      - personal (ForeignKey)
      """
      
def get_ia_response(text):
    api_key = '#'  # Reemplaza con tu API key de OpenAI
    url = 'https://api.openai.com/v1/chat/completions'
    prompt_message = f"""
    Aquí está el esquema de la base de datos:

    {STATIC_DATABASE_SCHEMA}
    
    El usuario ha solicitado lo siguiente :
    {text} , solo dame la consulta , solo la consulta niun texto mas , directo la consulta nada mas , ni un texto de mas solo la consulta , como : "SELECT * FROM tabla"
    """
    # Datos del cuerpo de la solicitud
    #prompt_message = f"Analiza el siguiente texto y genera una consulta SQL: {text}"  # Modificamos el prompt para generar SQL
    
    request_body = {
        "model": "gpt-3.5-turbo",  # Usa el modelo adecuado de OpenAI
        "messages": [
            {"role": "system", "content": "Eres un asistente útil que puede generar consultas SQL."},
            {"role": "user", "content": prompt_message}
        ]
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    try:
        # Realizar la solicitud POST a la API de OpenAI
        response = requests.post(url, json=request_body, headers=headers)
        
        # Si la solicitud es exitosa, obtener la respuesta en formato JSON
        response.raise_for_status()  # Lanza un error si la respuesta no es 2xx
        chat_response = response.json()
        
        # Obtener la consulta SQL generada por la IA
        sql_query = chat_response['choices'][0]['message']['content'].strip()
        
        sql_query_without_backticks = sql_query.replace("`", "")
        print(sql_query_without_backticks)
        
        return sql_query_without_backticks

    except requests.exceptions.RequestException as e:
        print(f"Error al consultar la API de ChatGPT: {e}")
        return "Hubo un error al procesar la solicitud."
    
    
def execute_sql_query(query):
    try:
        # Ejecutar la consulta SQL generada por la IA
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()  # Obtener los resultados de la consulta
        return result
    except Exception as e:
        print(f"Error al ejecutar la consulta SQL: {e}")
        return None


def analitics(request):
    result = []
    chart_data = {}
    if request.method == 'POST':
        input_text = request.POST.get('input_text')
        
        if input_text:
            # Paso 1: Obtener la consulta SQL generada por la IA
            sql_query = get_ia_response(input_text)  # Asume que esta función ya está implementada
            
            # Paso 2: Ejecutar la consulta SQL
            query_result = execute_sql_query(sql_query)
            
            if query_result:
                result = query_result  # Pasam


    context = {
        'result': result,
        'chart_data': chart_data,
    }
    return render(request, 'analitics.html', context)


# this handles the verification of email through a code sent to the user.
def verify_email(request):
    # this checks if the current request method is POST, meansing data has been submitted to the server.
    if request.method == 'POST':
        # Retrieve code from user input and session.
        user_input_code = request.POST.get('code')
        verification_code = request.session.get('verification_code')
        user_id = request.session.get('user_id')

        # this is Logging session and verification data - attempt details for debugging purposes
        logger.info(f"Verifying email: session data - user ID {user_id}, code {verification_code}")

        # this validates that all required information (code, and user ID) is present.
        if not all([user_input_code, verification_code, user_id]):
            messages.error(request, "Missing information required for verification.")
            return redirect('register')

        # Log available users in database for debugging
        users = User.objects.all()
        logger.info(f"Available users: {[user.username for user in users]}")

        try:
            # This attempts to fetch the user based on the user ID stored in the session.
            user = get_object_or_404(User, id=user_id)
            # this checks if the input code matches the session code.
            if user_input_code == str(verification_code):
                user.is_active = True #this marks the user as active (successfull email verification)
                user.save() # this saves the user and updates to the database.
                # this logs the user in automatically after email verification.
                login(request, user) 
                # this clears the session of the verification data to prevent reuse. 
                del request.session['verification_code']
                del request.session['user_id']
                # this then notifies the user of successful email verification and redirect to the 'scanner' view.
                messages.success(request, 'Email verified successfully!')
                return redirect('scanner')
            else:
                # If verification codes do not match, render the verification page with an error.
                messages.error(request, 'Invalid verification code.')
                return render(request, 'verify_email.html')
        except User.DoesNotExist:
            # this handles the case where the user ID does not correspond to any user in the database.
            messages.error(request, "No such user exists.")
            return redirect('register')
        except Exception as e:
            # this catchs all other exceptions and log them, providing a generic error message to the user.
            messages.error(request, f"Error during verification: {e}")
            return render(request, 'verify_email.html')
    else:
        # If the request method is not POST, simply render the email verification page.
        return render(request, 'verify_email.html')


# this function sends a verification email with SMTP protocol.
def send_verification_email(user, verification_code):
    # this checks if the user object has an email attribute that's not empty
    if not user.email:
        # this logs an error if the user object doesn't have an email address
        logger.error("No email address provided for user.")
        # means the user will exit the function returning False (email could not be sent)
        return False

    try:
        # this formats the message string with the verification code included
        message = f'Your verification code is: {verification_code}'
        # this makes a MIMEText object to specify the contents, type, and encoding of the email        
        msg = MIMEText(message, 'plain', 'utf-8')  
        # sets the subject line of the email
        msg['Subject'] = 'Verify Your Email'
        # sets the sender's email address
        msg['From'] = 'proyectostito12@gmail.com'
        # sets the recipient's email address
        msg['To'] = user.email

        # Logging the email details to ensure correctness
        logger.info(f"Email details: From: {msg['From']}, To: {msg['To']}")

        # this is to set up the SMTP server and establish a connection to the SMTP server at the specified address and port
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()  # Start TLS for security & Encrypt connection for security.
        s.login('proyectostito12@gmail.com', 'hnovcndqjdatddun')   # Log into the email server.
        s.sendmail(msg['From'], [msg['To']], msg.as_string()) # Send the email.
        s.quit() # this is to terminate the connection to the server.
        # this shows the successful sending of the email
        logger.info(f"Email sent to {user.email} with verification code {verification_code}")
        # this returns True indicating the email was successfully sent
        return True
    except Exception as e:
        # this catchs any exceptions during the email sending process and log an error
        logger.error(f"Failed to send email to {user.email}: {e}")
        # this return False indicating that sending the email failed
        return False

# This handles user login, authenticating credentials against the database.
def user_login(request):
    # This handles user login - checks if the current request is a POST request. 
    # This is necessary because sensitive data such as usernames and passwords 
    # should be sent via POST requests to ensure they are not visible in the URL.
    if request.method == "POST":
        # this retrieves the username and password from the POST request. 
       
        # these are expected to be provided by a login form where users enter their credentials.
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # this Uses Django's built-in `authenticate` method to verify the credentials. 
        # If the credentials are valid, it returns a User object. Otherwise, it returns None.
        user = authenticate(username=username, password=password) # Authenticate user.
        if user:
            # the `login` function from Django's auth module is called with the request and User object. 
            # this officially logs the user into the system, creating the appropriate session data.
            login(request, user) # Log the user in.
            # After successful login, redirect the user to scanner page. 
            #Here it redirects to a page named 'scanner'.
            return redirect('homekpi')
        else:
            
            # If authentication fails, display an error message and redirect back to the login form.            
            return render(request, 'login.html', {'error': 'Bad credentials, please try again'}, status=200)
    return render(request, 'login.html')

 
def custom_404(request, exception):
    return render(request, '404.html', status=404)


# logs out the user and redirects them to the home page.
def signout(request):
    # Handles user logout and redirects to home page
    logout(request) # uses logout function to terminate the user session.
    return redirect('home') # after logging out, redirect the user to the home page.

