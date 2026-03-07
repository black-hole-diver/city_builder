# ==========================================
# GRID DATA CONSTANTS
# ==========================================
class GridKey:
    TILE = "tile"
    COLLISION = "collision"
    RENDER_POS = "render_pos"
    GRID = "grid"
    CART_RECT = "cart_rect"
    ISO_POLY = "iso_poly"


class MusicEvent:
    JURASSIC_MUSIC = "assets/sounds/dino_song_epic.ogg"
    CREATION_SOUND = "assets/sounds/creation.ogg"
    DESTRUCTION_SOUND = "assets/sounds/destruction.ogg"
    BACKGROUND_MUSIC = "assets/sounds/fly_me_to_the_moon.ogg"
    WOOD_CHOP_SOUND = "assets/sounds/wood_chop.ogg"


# ==========================================
# EVENT CONSTANTS
# ==========================================
class GameEvent:
    RECALC_SATISFACTION = "recalculate_satisfaction"
    RECALC_SAT_AND_GROWTH = "recalculate_satisfaction_and_growth"
    PLAY_SOUND = "play_sound"
    NOTIFY = "notify"
    START_RAMPAGE = "start_rampage"
    TOGGLE_MUSIC = "toggle_music"
    EXECUTE_DEMOLITION = "execute_demolition"
    IGNORE_CLICKS = "ignore_clicks"
    UPDATE_POWER_CONNECTIVITY = "update_power_connectivity"
    INCREASE_TAX = "increase_tax"
    DECREASE_TAX = "decrease_tax"
    TAKE_LOAN = "take_loan"
    REPAY_LOAN = "repay_loan"


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
# ENTITY CONSTANTS
# ==========================================


class EntityType:
    ROAD = "Road"
    POWERLINE = "PowerLine"
    RES_ZONE = "ResZone"
    IND_ZONE = "IndZone"
    SER_ZONE = "SerZone"
    POLICE = "Police"
    STADIUM = "Stadium"
    FIRE_STATION = "FireStation"
    SCHOOL = "School"
    UNIVERSITY = "University"
    POWER_PLANT = "PowerPlant"
    VIP = "VIP"
    AXE = "Axe"
    HAMMER = "Hammer"
    TREE = "Tree"
    ROCK = "Rock"
    BLOCK = ""


# ==========================================
# BUILDING DIMENSIONS (Width, Height)
# ==========================================
BUILDING_SPECS = {
    EntityType.ROAD: (1, 1),
    EntityType.POWERLINE: (1, 1),
    EntityType.RES_ZONE: (4, 4),
    EntityType.IND_ZONE: (4, 4),
    EntityType.SER_ZONE: (4, 4),
    EntityType.POLICE: (2, 2),
    EntityType.STADIUM: (4, 4),
    EntityType.FIRE_STATION: (2, 2),
    EntityType.SCHOOL: (2, 2),
    EntityType.UNIVERSITY: (4, 4),
    EntityType.POWER_PLANT: (4, 4),
    EntityType.VIP: (1, 1),
}
# ==========================================
# COSTS OF BUILDINGS & ZONES
# ==========================================
COSTS = {
    EntityType.AXE: 0,
    EntityType.HAMMER: 0,
    EntityType.TREE: 100,
    EntityType.IND_ZONE: 50,
    EntityType.SER_ZONE: 50,
    EntityType.RES_ZONE: 50,
    EntityType.STADIUM: 5000,
    EntityType.POLICE: 500,
    EntityType.ROAD: 10,
    EntityType.FIRE_STATION: 500,
    EntityType.SCHOOL: 1000,
    EntityType.UNIVERSITY: 5000,
    EntityType.POWER_PLANT: 10000,
    EntityType.POWERLINE: 5,
    EntityType.VIP: 2000,
}
MAINTENANCE_FEES = {
    EntityType.ROAD: 1,
    EntityType.POLICE: 50,
    EntityType.STADIUM: 200,
    EntityType.FIRE_STATION: 50,
    EntityType.SCHOOL: 100,
    EntityType.UNIVERSITY: 500,
    EntityType.POWER_PLANT: 1000,
    EntityType.POWERLINE: 1,
    EntityType.RES_ZONE: 5,
    EntityType.IND_ZONE: 5,
    EntityType.SER_ZONE: 5,
}
ITEM_DESCRIPTIONS = {
    EntityType.AXE: "Clears trees for development.",
    EntityType.HAMMER: "Demolishes structures and rocks. Refunds part of the cost.",
    EntityType.TREE: "Forest tree. Increases nearby resident satisfaction.",
    EntityType.ROCK: "Blocks construction. Remove with Hammer.",
    EntityType.VIP: "Upgrades a zone to VIP: doubles capacity and adds luxury style.",
    EntityType.ROAD: "Required for commuting and zone development.",
    EntityType.POWERLINE: "Transfers electricity between separate areas.",
    EntityType.RES_ZONE: "Residential area. Homes build automatically if road-connected.",
    EntityType.IND_ZONE: "Industrial area. Provides jobs, lowers nearby residential satisfaction.",
    EntityType.SER_ZONE: "Service area. Provides jobs and balances industry.",
    EntityType.POLICE: "Ensures public safety within its radius.",
    EntityType.STADIUM: "Large satisfaction boost nearby.",
    EntityType.FIRE_STATION: "Reduces fire risk and responds to emergencies.",
    EntityType.SCHOOL: "Secondary education. Increases income and taxes.",
    EntityType.UNIVERSITY: "Tertiary education. Maximizes income and taxes.",
    EntityType.POWER_PLANT: "Generates electricity. Must connect to zones or power lines.",
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
