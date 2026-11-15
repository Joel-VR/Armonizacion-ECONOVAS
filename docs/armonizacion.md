# Propuesta de armonización de puntos críticos: MODIS y VIIRS Suomi NPP

## 1. Objetivo y alcance

Construir un calendario de **actividad térmica detectada** comparable en el tiempo y el espacio, a partir de MODIS (Terra y Aqua) y VIIRS de Suomi NPP. El resultado es un indicador relativo de actividad observada, no una estimación directa del número de incendios, del área quemada ni de la probabilidad real de incendio.

Esta es una propuesta para un prototipo: sus parámetros y su capacidad de comparación deben validarse antes de utilizarla en decisiones operativas. Los archivos disponibles cubren desde el 1 de enero de 2016; no constituyen por sí solos un registro de más de dos décadas.

## 2. Datos disponibles

| Fuente | Histórico | NRT | Satélite |
|---|---|---|---|
| MODIS C6.1 | 2016-01-01 a 2026-08-31; 161.361 registros | 2026-09-01 a 2026-11-13; 4.264 | Terra y Aqua |
| VIIRS C2 | 2016-01-01 a 2026-07-31; 785.884 registros | 2026-08-01 a 2026-11-01; 43.565 | Suomi NPP |

Las fechas indican los extremos encontrados, no garantizan cobertura diaria. El NRT de Suomi termina antes que el de MODIS. Los archivos históricos y NRT se deben distinguir: los NRT son provisionales y pueden ser reemplazados cuando FIRMS publique datos estándar. El histórico MODIS contiene valores de versión `6.03` y `61.03`; conservarlos para examinar posibles discontinuidades.

## 3. Qué se armoniza

MODIS y VIIRS tienen distinta resolución, sensibilidad, horas de observación y cobertura. VIIRS puede detectar focos pequeños que MODIS no detecta. No existe aquí una constante validada para convertir un punto MODIS en cierta cantidad de puntos VIIRS. Tampoco debe sumarse FRP entre sensores como si las observaciones fueran independientes.

La propuesta tiene dos niveles:

1. **Medida por sensor:** celdas con al menos una detección por día, agregadas por semana para el área de interés.
2. **Índice relativo armonizado:** posición de la actividad semanal respecto al historial de la misma fuente y época del año; se combinan los índices solo cuando ambos están disponibles y la comparación ha sido evaluada.

El índice es una aproximación estadística a patrones relativos, no una calibración física ni una corrección completa de la diferente sensibilidad o cobertura.

## 4. Preparación

### 4.1 Normalizar y conservar procedencia

Para cada registro conservar: coordenadas WGS84, fecha y hora UTC, satélite, sensor normalizado, versión, origen histórico/NRT, confianza original, tipo, FRP, día/noche y un identificador de fuente. En Suomi, el campo original `instrument` contiene `SNPP`: normalizarlo a `VIIRS` sin perder el valor original. Mantener Terra y Aqua identificados dentro de MODIS.

Interpretar `acq_time` como HHMM UTC, preservando ceros iniciales; combinarlo con `acq_date`. Usar días y semanas UTC de manera uniforme. Si la interfaz ofrece tiempo local, convertir el instante a la zona seleccionada **antes** de agrupar y recalcular toda la línea base con la misma zona.

Verificar JSON, fechas, hora, coordenadas, valores y campos obligatorios. Registrar y excluir filas inválidas con motivos. Eliminar únicamente duplicados exactos verificables dentro de una misma fuente y versión, dejando trazabilidad; no eliminar observaciones cercanas de diferentes pasadas como si fueran duplicados seguros.

### 4.2 Calidad y tipo

Como configuración inicial, usar todas las categorías de confianza y conservarlas para filtros y análisis de sensibilidad; MODIS usa una escala numérica y VIIRS categorías, que no son equivalentes. Los históricos incluyen `type`, pero los NRT revisados no: marcarlo como **desconocido**, nunca como incendio de vegetación por defecto. Permitir filtrar los tipos conocidos y documentar el efecto de incluir los desconocidos. No afirmar que todos los puntos son incendios forestales o agrícolas: algunas anomalías pueden tener otro origen.

Registrar qué archivo, versión, filtros y fecha de procesamiento se utilizaron. Al recibir una actualización, reemplazar el periodo provisional por el producto estándar correspondiente cuando esté disponible, evitando mezclar ambas versiones del mismo registro, y recalcular agregados afectados.

## 5. Agregación espacial y temporal

1. Seleccionar el área de interés (AOI) e incluir los puntos cuyo centro cae dentro de ella. La selección por centro es una aproximación: el píxel observado tiene una huella de tamaño variable.
2. Usar una cuadrícula fija de **5 km × 5 km** en una proyección métrica apropiada para la región; para áreas extensas o globales usar una cuadrícula de área equivalente. Mantener CRS, origen y tamaño de celda constantes en todos los años y sensores. Los 5 km son un parámetro inicial, no una resolución efectiva del sensor ni un valor científicamente óptimo.
3. Dividir el tiempo en días UTC y semanas ISO. Por sensor `s`, celda `c` y día `d` definir:

   `I(s,c,d) = 1 si existe al menos una detección válida; 0 si no existe ninguna`

4. Para una semana `w` calcular:

   `A(s,w) = suma de I(s,c,d), para las celdas de la AOI y días de w`

   La unidad es **celdas-día con detección**. Varias detecciones del mismo sensor, incluidas Terra y Aqua, en una celda y día cuentan una vez. La misma celda activa en dos días cuenta dos veces. No equivale a incendios únicos ni a superficie quemada.

Ejemplo: si MODIS detecta tres puntos en la celda A el lunes y uno en A el martes, y VIIRS detecta cinco en A el lunes y uno en la celda B el martes, entonces `A(MODIS,w)=2` y `A(VIIRS,w)=2`. Sus puntos no se suman para producir un número de incendios.

Para un AOI pequeña, una cuadrícula de 5 km puede ser demasiado gruesa y el indicador discreto: mostrar esta limitación y probar otras escalas. Mantener el área fija al comparar años; si cambia, recalcular la línea base para la nueva geometría.

## 6. Línea base estacional e índice

Elegir inicialmente **2016–2024** como periodo de referencia común y fijo, excluyendo 2025–2026 para probar el método en datos posteriores. Usar solo semanas completas dentro del periodo, con filtros idénticos. Esta elección es provisional: verificar disponibilidad y calidad por fuente, año y estación; no interpretar el hecho de tener registros como prueba de cobertura válida.

Para la semana objetivo `w`, construir por separado para cada sensor `s` una muestra de referencia `B(s,w)` con los valores semanales de los años base correspondientes a la misma semana estacional y las **dos semanas vecinas a cada lado** (ventana circular de cinco semanas). Excluir el año objetivo de la muestra cuando este pertenezca a la línea base. Para la semana ISO 53 usar la ventana circular alrededor de la transición de año y documentar la regla aplicada; no tratarla como una estación independiente.

Para un valor observado `A(s,w)`, calcular su percentil empírico con tratamiento de empates:

`P(s,w) = [n(A_ref < A(s,w)) + 0,5 × n(A_ref = A(s,w))] / n(B(s,w))`

El resultado está entre 0 y 1. Un valor próximo a 0,9 significa que la actividad observada es alta respecto a esa muestra histórica del mismo sensor y temporada; **no** significa un 90 % de probabilidad de incendio. Exigir al menos 20 semanas de referencia y cinco años distintos; si no se cumplen, devolver «línea base insuficiente». Estos umbrales son parámetros iniciales sujetos a validación. Con muchos ceros o empates, el percentil pierde discriminación; mostrar el valor bruto, el tamaño de muestra y una advertencia, sin forzar una categoría.

Clasificación ilustrativa, solo si hay suficiente información:

| Percentil | Etiqueta |
|---|---|
| Menor que 0,25 | Bajo respecto al historial |
| 0,25 a menos de 0,75 | Habitual |
| 0,75 a menos de 0,90 | Alto |
| 0,90 o mayor | Muy alto |

Estos cortes son de presentación y no definen un umbral oficial de alerta. Comparar también distribuciones de valores absolutos, porque percentiles similares no significan igual cantidad de detecciones.

## 7. Combinación de sensores

Para una semana con ambos indicadores utilizables, una regla inicial transparente es:

`H(w) = [P(MODIS,w) + P(VIIRS,w)] / 2`

Ejemplo: si MODIS tiene percentil 0,80 y VIIRS 0,90, `H = 0,85`. Mostrar siempre `H` junto con ambos percentiles, valores `A` y procedencia. Si difieren en más de **0,25**, marcar «sensores discrepan»; este umbral también es provisional. No interpretar el promedio como medición física, probabilidad, área o número de incendios. Los pesos iguales son una decisión de producto, no una calibración demostrada.

Si solo uno de los dos indicadores está disponible, mostrar su resultado **por separado**, con la fuente y el aviso «un solo sensor»; no etiquetarlo como el mismo índice combinado. Si ninguno es utilizable, mostrar «información insuficiente». La fecha posterior al último registro de Suomi no debe tratarse como si Suomi hubiera observado cero.

## 8. Cobertura: una limitación esencial

Los archivos de puntos solo informan detecciones positivas. **No permiten distinguir por sí solos** una semana sin fuego de una semana sin observación útil por nubes, humo, fallas o ausencia de pasada. Por tanto, los ceros de la fórmula de la sección 5 significan «sin detecciones registradas», no «sin fuego» ni «observación confirmada». Los indicadores basados solo en estos JSON son exploratorios y no deben presentarse como actividad baja confirmada.

Para una versión robusta, incorporar máscaras o productos de cobertura, nubes y calidad por sensor, celda y día. Con esa información, definir `O(s,c,d)=1` únicamente si hubo observación utilizable y `0` si no; una ausencia de detección solo es cero confirmado cuando `O=1`. Calcular y mostrar la fracción de celdas-día observables y, cuando sea insuficiente, informar «cobertura insuficiente» en vez de clasificar. Definir y validar el umbral de cobertura según el producto. Una posible tasa exploratoria es `T = celdas-día con detección / celdas-día observables`, con línea base construida usando la misma regla; requiere verificar la correspondencia entre detecciones y observaciones útiles. Sin esos productos no se puede calcular ni asumir esta tasa.

## 9. Validación antes de llamar al resultado armonizado

- Revisar cobertura temporal real, cambios de versión, proporciones día/noche y cantidad por satélite, mes y año. No atribuir automáticamente los cambios a la actividad de quema.
- Con los mismos filtros y AOI, contrastar los indicadores de ambos sensores durante el solapamiento: gráficas semanales, correlación, discrepancias estacionales y proporción de semanas con clasificaciones distintas. Correlación alta no demuestra equivalencia.
- Evaluar fuera de muestra en 2025–2026 usando la línea base fija de 2016–2024. Revisar por separado el cambio de histórico a NRT; el periodo parcial de 2026 no debe compararse con años completos.
- Probar sensibilidad con celdas de 2, 5 y 10 km, distintas ventanas estacionales y filtros de confianza y tipo. Documentar cuánto cambian los resultados y dónde la muestra es escasa.
- Contrastar una muestra de semanas con imágenes, información de cobertura y, si existen, registros independientes de incendios. Reportar incertidumbre, omisiones y diferencias entre sensores. No seleccionar parámetros únicamente porque hacen coincidir las series.
- Si hay desacuerdo persistente o cobertura desconocida, mostrar las series por separado y describir el índice combinado como experimental; no afirmar que se ha obtenido una serie científicamente equivalente.

## 10. Salida sugerida en la aplicación

Para cada área y semana mostrar: celdas-día detectadas por sensor, percentiles y línea base utilizada, indicador combinado cuando proceda, discrepancia, fuentes y versiones, periodo provisional, cobertura conocida o desconocida y limitaciones. Permitir consultar un calendario histórico y un mapa de detecciones; no describirlos como superficie quemada ni como una alerta táctica.

## Referencias

- [NASA FIRMS: README de descarga](https://firms.modaps.eosdis.nasa.gov/download/Readme.txt).
- [NASA: atributos de MODIS y VIIRS](https://www.earthdata.nasa.gov/data/tools/firms/active-fire-data-attributes-modis-viirs).
- [NASA: características y resolución de los sensores](https://wiki.earthdata.nasa.gov/spaces/FIRMS/blog/2022/09/29/266967967/Characteristics%2Bof%2BVIIRS%2BMODIS%2Band%2BOLI%2BSensors%2Band%2BTheir%2BEffects%2Bon%2Bthe%2BSpatial%2BExtent%2Bof%2BDaily%2BActive%2BFire%2BData).
- [NASA: por qué un incendio puede no detectarse](https://forum.earthdata.nasa.gov/viewtopic.php?t=5178).
- [NASA: impacto de las nubes en las detecciones](https://wiki.earthdata.nasa.gov/spaces/FIRMS/blog/2024/08/07/382276882/The%2BImpact%2Bof%2BCloud%2Bon%2BActive%2BFire%2BDetections).


## Tabla semanal generada

La tabla PostgreSQL `datos_armonizados` almacena una fila por departamento, año y semana ISO para el método experimental con cuadrícula de 5 km. Conserva por separado los valores de celdas-día, los percentiles y el tamaño de muestra de MODIS y VIIRS Suomi, además de la fracción de empates, el índice combinado cuando es comparable y su estado. Incluye la zona EPSG empleada, la referencia 2016–2024, el último registro encontrado por fuente y la fecha de cálculo. Las semanas que cruzan el año se registran como incompletas.

La generación utiliza las observaciones asignadas a un departamento de `modis` (Terra y Aqua) y `viirs` (solo `SNPP`). NOAA-20 y NOAA-21 permanecen en la tabla original y no participan en este método. Se incluyen todas las categorías de confianza y tipo, incluidos los tipos desconocidos; los registros sin departamento no se agregan. El dato de último registro es únicamente el extremo encontrado, no demuestra cobertura diaria. La columna `cobertura` se marca como desconocida y el índice continúa siendo experimental y no validado.

El esquema se define en `backend/sql/migrations/002_crear_datos_armonizados.sql` y el cálculo en `data-pipeline/generar_datos_armonizados.py`. El generador exige una tabla armonizada vacía y no sobrescribe resultados; si cambian los datos de origen, debe planificarse explícitamente su regeneración. Las tablas originales no se modifican. Las vistas anteriores todavía deben adaptarse al nuevo esquema de datos.
