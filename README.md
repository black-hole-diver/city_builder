# Isometric City Builder

A tycoon-like real-time city builder game built with Python and Pygame. As the mayor, you are tasked with developing a prosperous city, managing the economy, and keeping your citizens satisfied. 

This engine features a fully functional 2.5D isometric grid system, dynamic multi-tile building placement, interactive tools, and a real-time calendar system.

## ELTE University Task Description

This project is based on an assignment for the Software Technology Practice course. It was assigned during the 2022/2023 Spring Semester at the ELTE Faculty of Informatics. 

The core requirements and objectives of the task include:
* **Core Concept**: Implement a tycoon-like real-time city builder game. The gameplay should be similar to the Sim City series. 
* **Player Role**: The player acts as a mayor managing a well-defined area of square fields. The main goal is to build a prosperous city where citizens are happy and the budget remains balanced.
* **Zoning & Growth**: The player can assign residential, industrial, and service zones. Citizens will automatically build apartments and workplaces in these designated zones at no additional cost. 
* **Infrastructure**: Citizens will only build on a zone if it is accessible from a public road on at least one side. Citizens must also be able to travel via public road from their residence to their workplace.
* **Service Buildings**: The player must manually construct and pay annual maintenance fees for service buildings. Examples include Police stations (for public safety) and Stadiums (which occupy a 2x2 area and boost satisfaction).
* **Economy**: The player receives starting capital but must eventually rely on tax revenues. An annual fixed tax amount can be levied on each populated zone space. 
* **Time Management**: The game plays in real-time but much faster than reality. The UI must display the date (year, month, day), and allow the player to run the game at 3 different speeds or pause it.
* **Persistence**: It should be possible to save and load the game, and to manage multiple saves.
* **Graphics**: While the basic requirement is a 2D top-down view, bonus points are awarded for implementing 2.5-dimensional isometric graphics where buildings visually extend beyond their base cell.

## Current Features

* **2.5D Isometric Engine:** Procedurally generated terrain using Perlin noise with fully mathematically calculated isometric projection and depth-sorting.
* **Multi-Tile Support:** Support for large structures (e.g., 4x4 Residential Zones, 2x2 Stadiums) that correctly span multiple grid coordinates.
* **Time & Speed Controls:** A functional calendar system that drives simulation logic. Players can pause (`SPACE`) or cycle between 1x, 2x, and 3x speeds.
* **Save/Load Management:** An interactive UI overlay to manage up to 3 separate save slots, writing serialized game states to JSON.
* **Interactive Tool System:** Object-oriented tools (Axe, Hammer) to manipulate the environment, harvest resources, and clear land.
* **Dynamic HUD:** Context-aware tooltips, item cost calculations, and an interactive examination panel for reviewing building and scenery statistics.

## Controls

* **Left Click**: Place buildings, use selected tool, or select objects to examine.
* **Right Click**: Deselect current tool or building.
* **Mouse Movement**: Pan the camera to scroll across the map.
* **Spacebar**: Pause / Unpause the game simulation.
* **1, 2, 3**: Change simulation speed (1x, 2x, 3x).
* **ESC**: Close open menus or quit the game.

## Installation & Running

1. Ensure you have Python 3.x installed.
2. Install the required dependencies:
   ```bash
   pip install pygame
   pip install noise
   
3. Run the main game file:
   ```bash
   python main.py