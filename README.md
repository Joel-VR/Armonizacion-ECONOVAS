# Brinco Alerta

Brinco Alerta es un proyecto para explorar observaciones satelitales relacionadas con el estudio de incendios forestales y quemas agrícolas, con un enfoque inicial en Huánuco y Perú. Reúne una interfaz web, una API y un pipeline para importar observaciones JSON de NASA FIRMS. Su identidad visual utiliza un conejo bombero como símbolo de protección de la vida silvestre.

> Una detección de anomalía térmica no confirma por sí sola un incendio ni su causa. El proyecto consulta datos MODIS y VIIRS Suomi cargados en PostgreSQL/PostGIS. El indicador relativo de los departamentos del Perú entre 2016 y 2026 es experimental y no está validado.

Consulte [instalación y carga de datos](docs/instalacion.md), [arquitectura](docs/arquitectura.md) y [metodología propuesta](docs/armonizacion.md) y [uso de datos por departamento](docs/datos-departamentos-peru.md).

## Ejecutar el frontend

Requiere Node.js 22.13 o superior en la rama 22, o una versión LTS posterior compatible con las dependencias.

```powershell
cd frontend
npm ci
npm run dev
```

Abra la dirección indicada por Vite. Para comprobar el frontend antes de hacer push:

```powershell
npm test
npm run build
```

Las imágenes satelitales de Esri requieren conexión. Consulte [fuentes y limitaciones](docs/fuentes-limitaciones.md) y [arquitectura](docs/arquitectura.md).
