# ==========================================
# CORE GAME SETTINGS
# ==========================================
TILE_SIZE = 64
WORKER_SPEED = 180
INITIAL_WORKER = 10

# ==========================================
# POPULATION & GROWTH SETTINGS
# ==========================================
GROWTH_SATISFACTION_THRESHOLD = 50  # Satisfaction needed to gain citizens
DECLINE_SATISFACTION_THRESHOLD = 30  # Satisfaction level where people start leaving
BASE_GROWTH_RATE = 3  # Standard number of people moving in
STARTER_CITY_BOOST = 5
STARTER_POPULATION_LIMIT = 20  # Scaled up to match the new massive numbers
GROWTH_SCALER = 2  # Huge bonus growth per satisfaction point (Lower = faster)
BASE_DECLINE_RATE = -3  # Number of people who leave per day when unhappy

# ==========================================
# ZONE SETTINGS
# ==========================================
ZONE_CAPACITY = 100  # Max people per zone tile
ZONE_REFUND_PERCENT = 0.5  # 50% refund if empty
BUILDING_REFUND_PERCENT = 0.5

# Satisfaction influence radiuses
POLICE_RADIUS = 10
STADIUM_RADIUS = 15
INDUSTRIAL_NEGATIVE_RADIUS = 8

# Power Plant Supply
POWER_PLANT_SUPPLY = 5000

# ==========================================
# CAMERA & DISPLAY
# ==========================================
MAP_WIDTH = 6400
MAP_HEIGHT = 3328
MARGIN = 500

BACKGROUND_COLOR = (19, 38, 92)
WHITE = (255, 255, 255)
HUD_COLOR = (27, 27, 27, 175)

# ==========================================
# TIME & SPEED
# ==========================================
SPEEDS = {1: 5_000, 2: 2_500, 3: 400, 4: 100}

# ==========================================
# BUILDING DIMENSIONS (Width, Height)
# ==========================================
BUILDING_SPECS = {
    # Infrastructure & Zones (1x1)
    "Road": (1, 1),
    "PowerLine": (1, 1),
    "ResZone": (4, 4),
    "IndZone": (4, 4),
    "SerZone": (4, 4),
    # Basic Services
    "Police": (2, 2),
    "Stadium": (4, 4),
    # Advanced Services
    "FireStation": (2, 2),
    "School": (2, 2),
    "University": (4, 4),
    "PowerPlant": (4, 4),
    "VIP": (1, 1),
}

# ==========================================
# COSTS OF BUILDINGS & ZONES
# ==========================================
COSTS = {
    "Axe": 0,
    "Hammer": 0,
    "Tree": 100,
    "IndZone": 50,
    "SerZone": 50,
    "ResZone": 50,
    "Stadium": 5000,
    "Police": 500,
    "Road": 10,
    "FireStation": 500,
    "School": 1000,
    "University": 5000,
    "PowerPlant": 10000,
    "PowerLine": 5,
    "VIP": 2000,
}
MAINTENANCE_FEES = {
    "Road": 1,
    "Police": 50,
    "Stadium": 200,
    "FireStation": 50,
    "School": 100,
    "University": 500,
    "PowerPlant": 1000,
    "PowerLine": 1,
    "ResZone": 5,
    "IndZone": 5,
    "SerZone": 5,
}
ITEM_DESCRIPTIONS = {
    # Tools & Nature
    "Axe": "Clears trees for development.",
    "Hammer": "Demolishes structures and rocks. Refunds part of the cost.",
    "Tree": "Forest tree. Increases nearby resident satisfaction.",
    "Rock": "Blocks construction. Remove with Hammer.",
    "VIP": "Upgrades a zone to VIP: doubles capacity and adds luxury style.",
    # Infrastructure
    "Road": "Required for commuting and zone development.",
    "PowerLine": "Transfers electricity between separate areas.",
    # Zones
    "ResZone": "Residential area. Homes build automatically if road-connected.",
    "IndZone": "Industrial area. Provides jobs, lowers nearby residential satisfaction.",
    "SerZone": "Service area. Provides jobs and balances industry.",
    # Services
    "Police": "Ensures public safety within its radius.",
    "Stadium": "Large satisfaction boost nearby.",
    "FireStation": "Reduces fire risk and responds to emergencies.",
    "School": "Secondary education. Increases income and taxes.",
    "University": "Tertiary education. Maximizes income and taxes.",
    "PowerPlant": "Generates electricity. Must connect to zones or power lines.",
}


# ==========================================
# ASSET URLs
# ==========================================

# Tools & UI
HAMMER_URL = "assets/graphics/hammer.png"
AXE_URL = "assets/graphics/axe.png"


# Worker, Dinosaur, Car, Firetruck
DINOSAUR_URL = "assets/graphics/Dinosaur.png"
WORKER_URL = "assets/graphics/worker.png"
CAR_URL = "assets/graphics/Car.png"
FIRETRUCK_URL = "assets/graphics/FireTruck.png"

# Environment
BLOCK_URL = "assets/graphics/block.png"
TREE_URL = "assets/graphics/tree.png"
ROCK_URL = "assets/graphics/rock.png"

# Infrastructure & Entities
ROAD_URL = "assets/graphics/Road.png"
POWERLINE_URL = "assets/graphics/Powerline.png"

# Service Buildings
POLICE_URL = "assets/graphics/Police.png"
STADIUM_URL = "assets/graphics/Olympic.png"
FIRE_STATION_URL = "assets/graphics/FireStation.png"
SCHOOL_URL = "assets/graphics/School.png"
UNIVERSITY_URL = "assets/graphics/University.png"
POWERPLANT_URL = "assets/graphics/PowerPlant.png"

# Residential Zones
RESZONE_URL1 = "assets/graphics/ResZone1.png"
RESZONE_URL2 = "assets/graphics/ResZone2.png"
RESZONE_URL3 = "assets/graphics/ResZone3.png"

# Industrial Zones
INDZONE_URL1 = "assets/graphics/IndZone1.png"
INDZONE_URL2 = "assets/graphics/IndZone2.png"
INDZONE_URL3 = "assets/graphics/IndZone3.png"

# Service Zones
SERZONE_URL1 = "assets/graphics/SerZone1.png"
SERZONE_URL2 = "assets/graphics/SerZone2.png"
SERZONE_URL3 = "assets/graphics/SerZone3.png"

# VIP Zones
RESZONE_URL4 = "assets/graphics/ResZone4.png"
INDZONE_URL4 = "assets/graphics/IndZone4.png"
SERZONE_URL4 = "assets/graphics/SerZone4.png"
VIP_URL = "assets/graphics/vip.png"

# FIRE VARIABLES
FIRE_URL = "assets/graphics/Fire.png"
FIRE_SPREAD_TIME = 30000  # 30 seconds in milliseconds
FIRE_STATION_RADIUS = 20  # Tiles
CHANCE = 0.001

# ==========================================
# AI GENERATION PROMPTS
# ==========================================
PROMPT = "Modify these items I am giving you to match the isometric low-poly stylized 3D aesthetic \
    of a mobile tycoon game in a stylized low-poly isometric game art style, 3D render, minimalist \
        design, matte plastic texture, vibrant colors, soft ambient occlusion, toy-like aesthetic, \
            white background, high-quality game asset, solar punk."
