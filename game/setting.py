# ==========================================
# CORE GAME SETTINGS
# ==========================================
TILE_SIZE = 64
WORKER_SPEED = 180
INITIAL_WORKER = 10

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
SPEEDS = {
    1: 15_000,
    2: 10_000,
    3: 3_000
}

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
    "PowerPlant": (4, 4)
}

# ==========================================
# ASSET URLs
# ==========================================

# Tools & UI
HAMMER_URL = "assets/graphics/hammer.png"
AXE_URL = "assets/graphics/axe.png"

# Environment
BLOCK_URL = "assets/graphics/block.png"
TREE_URL = "assets/graphics/tree.png"
ROCK_URL = "assets/graphics/rock.png"

# Infrastructure & Entities
ROAD_URL = "assets/graphics/Road.png"
POWERLINE_URL = "assets/graphics/Powerline.png"
WORKER_URL = "assets/graphics/worker.png"
CAR_URL = "assets/graphics/Car.png"
FIRETRUCK_URL = "assets/graphics/Firetruck.png"

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

# ==========================================
# AI GENERATION PROMPTS
# ==========================================
PROMPT = "Modify these items I am giving you to match the isometric low-poly stylized 3D aesthetic of a mobile tycoon game in a stylized low-poly isometric game art style, 3D render, minimalist design, matte plastic texture, vibrant colors, soft ambient occlusion, toy-like aesthetic, white background, high-quality game asset, solar punk."