"""Business niches (Portuguese and English) mapped to Geoapify categories.

Keys are compared after search_key (lowercase, no accents) and hyphen removal.
"""

NICHES: dict[str, list[str]] = {
    # Hairdresser covers both hair salons and barbers; the API has no barber-only category.
    "service.beauty.hairdresser": [
        "barbearia", "barbearias", "salao de beleza", "saloes de beleza", "salao", "saloes",
        "cabeleireiro", "cabeleireiros", "cabeleireira", "cabeleireiras",
        "barbershop", "barbershops", "barber", "barbers", "beauty salon", "beauty salons", "hair salon", "hair salons",
    ],
    "service.beauty.spa": ["spa", "spas", "estetica", "clinica de estetica", "clinicas de estetica"],
    "service.beauty.massage": ["massagem", "massoterapia", "massoterapeuta", "massage"],
    "service.beauty.tattoo": ["tatuagem", "estudio de tatuagem", "estudios de tatuagem", "tatuador", "tatuadores",
                              "tattoo", "tattoo studio", "tattoo studios"],
    "catering.restaurant": ["restaurante", "restaurantes", "restaurant", "restaurants"],
    "catering.restaurant.pizza": ["pizzaria", "pizzarias", "pizza", "pizzeria", "pizzerias"],
    "catering.fast_food": ["lanchonete", "lanchonetes", "fast food"],
    "catering.fast_food.burger": ["hamburgueria", "hamburguerias", "burger", "burgers"],
    "catering.cafe": ["cafeteria", "cafeterias", "cafe", "cafes", "coffee shop", "coffee shops"],
    "catering.bar": ["bar", "bares", "bars"],
    "catering.ice_cream": ["sorveteria", "sorveterias", "ice cream"],
    "commercial.food_and_drink.bakery": ["padaria", "padarias", "bakery", "bakeries"],
    "commercial.food_and_drink.confectionery": ["confeitaria", "confeitarias", "doceria", "docerias", "confectionery"],
    "commercial.food_and_drink.butcher": ["acougue", "acougues", "butcher", "butchers"],
    "commercial.supermarket": ["supermercado", "supermercados", "mercado", "mercados", "supermarket", "supermarkets"],
    "healthcare.dentist": ["dentista", "dentistas", "odontologia", "clinica odontologica", "clinicas odontologicas",
                           "consultorio odontologico", "dentist", "dentists"],
    "healthcare.clinic_or_praxis": ["clinica", "clinicas", "clinica medica", "clinicas medicas", "consultorio",
                                    "consultorios", "medico", "medicos", "clinic", "clinics"],
    "healthcare.clinic_or_praxis.dermatology": ["dermatologista", "dermatologistas", "dermatologia"],
    "healthcare.pharmacy": ["farmacia", "farmacias", "drogaria", "drogarias", "pharmacy", "pharmacies"],
    "commercial.health_and_beauty.optician": ["otica", "oticas", "optician", "opticians"],
    "commercial.health_and_beauty.cosmetics": ["cosmeticos", "loja de cosmeticos", "lojas de cosmeticos", "cosmetics"],
    "sport.fitness": ["academia", "academias", "gym", "gyms", "fitness"],
    "sport.dojo": ["artes marciais", "dojo", "dojos", "martial arts"],
    "pet.veterinary": ["veterinario", "veterinarios", "veterinaria", "clinica veterinaria", "clinicas veterinarias",
                       "vet", "vets", "veterinary"],
    "commercial.pet": ["pet shop", "pet shops", "petshop", "petshops"],
    "pet.service": ["banho e tosa", "pet grooming"],
    "accommodation.hotel": ["hotel", "hoteis", "hotels"],
    "accommodation.guest_house": ["pousada", "pousadas", "guest house", "guest houses"],
    "service.vehicle.repair.car": ["oficina", "oficinas", "oficina mecanica", "oficinas mecanicas", "mecanica",
                                   "mecanico", "auto repair", "car repair"],
    "service.vehicle.car_wash": ["lava jato", "lava jatos", "lava rapido", "lavagem automotiva", "car wash"],
    "office.lawyer": ["advogado", "advogados", "advocacia", "escritorio de advocacia", "escritorios de advocacia",
                      "lawyer", "lawyers"],
    "office.accountant": ["contador", "contadores", "contabilidade", "escritorio de contabilidade",
                          "escritorios de contabilidade", "accountant", "accountants"],
    "office.estate_agent": ["imobiliaria", "imobiliarias", "corretor de imoveis", "real estate", "real estate agency"],
    "education.driving_school": ["autoescola", "autoescolas", "auto escola", "auto escolas", "driving school"],
    "education.language_school": ["escola de idiomas", "escolas de idiomas", "curso de ingles", "cursos de idiomas",
                                  "language school", "language schools"],
    "education.music_school": ["escola de musica", "escolas de musica", "music school"],
    "commercial.florist": ["floricultura", "floriculturas", "florista", "florist", "florists"],
    "commercial.clothing": ["loja de roupas", "lojas de roupas", "boutique", "boutiques", "clothing store"],
    "commercial.jewelry": ["joalheria", "joalherias", "jewelry", "jewelry store"],
    "commercial.furniture_and_interior": ["moveis", "loja de moveis", "lojas de moveis", "furniture store"],
    "commercial.houseware_and_hardware": ["material de construcao", "materiais de construcao", "loja de construcao",
                                          "ferragens", "hardware store"],
    "service.photographer": ["fotografo", "fotografos", "fotografa", "estudio fotografico", "photographer"],
    "service.tailor": ["costureira", "costureiras", "alfaiate", "alfaiates", "tailor"],
    "service.cleaning": ["lavanderia", "lavanderias", "laundry"],
}

CATEGORIES = {alias: category for category, aliases in NICHES.items() for alias in aliases}

# Categories whose businesses usually work by appointment (prefix match).
APPOINTMENT_CATEGORIES = (
    "service.beauty", "healthcare.dentist", "healthcare.clinic_or_praxis", "pet.veterinary", "pet.service",
)
