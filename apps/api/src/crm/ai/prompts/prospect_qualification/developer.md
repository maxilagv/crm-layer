# Formato de salida

Devolve un unico JSON con:

- **fit_score**: entero 0-100 segun la rubrica.
- **qualified**: boolean (true cuando fit_score >= {min_fit_score}).
- **signals**: lista de senales del vocabulario (negativas y positivas).
- **reasoning**: 1-2 frases (hasta 3 si esta cerca del umbral) que muestren el trade-off.
- **recommended_angle**: la senal mas persuasiva atada a un resultado concreto, lista para el primer mensaje.
- **confidence**: numero 0-1; bajala si la huella tiene pocos datos.

## Template
Campana: {campaign_vertical}
Perfil objetivo de la campana:
{campaign_target_profile}
Umbral de calificacion de esta campana: {min_fit_score}

Huella del prospecto (lo que pudimos investigar):
{prospect_profile}
