#include "skye.h"   // Contains the 'skye' array (uint16_t[])
#include "rubble.h" // Contains the 'rubble' array (uint16_t[])
#include "marshall.h" // Contains the 'marshall' array (uint16_t[])
#include <TFT_eSPI.h>
#include <SPI.h>
#include <RotaryEncoder.h>
#include <FunctionalInterrupt.h> // Required for std::bind on ESP32

// --- Configuration Constants ---
#define NUM_IMAGES   3       // Number of character images
#define IMAGE_HEIGHT 128     // Display/Image height in pixels
#define IMAGE_WIDTH  128     // Display/Image width in pixels
const int buttonPin = 12;    // GPIO pin for the encoder's button
const unsigned long updateInterval = 250; // Minimum ms between display updates
const long buttonDebounceDelay = 50;     // Milliseconds for button debounce

// --- Global Variables ---
// Image data array
const uint16_t* imageArray[NUM_IMAGES] = { rubble, skye, marshall };
const char* characterNames[NUM_IMAGES] = { "Rubble", "Skye", "Marshall" };
TFT_eSPI tft = TFT_eSPI();             // TFT display object

// Encoder variables
RotaryEncoder encoder1(32, 33, RotaryEncoder::LatchMode::FOUR0); // Encoder pins 32, 33
unsigned long lastUpdateTime = 0;       // Stores the time (in ms) of the last screen update

// State variables
int selectedIndex = 0;      // Index currently SHOWN on display
bool buttonIsPressed = false; // Logical state of the button (debounced, LOW = pressed)

// --- Function Prototypes ---
void drawSelections(int index);
void sendSelection();

// --- Setup Function ---
void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 2000); // Wait for Serial or timeout
  Serial.println("\n--- Starting Character Selector ---");

  Serial.println("Initializing TFT...");
  tft.init();
  tft.setRotation(0); // Adjust rotation if needed

  Serial.println("Setting Pin Modes...");
  pinMode(buttonPin, INPUT_PULLUP); // Encoder button pin with internal pull-up

  Serial.println("Setting up Encoder...");
  encoder1.setPosition(0);         // Reset encoder count to zero
  lastUpdateTime = millis();       // Initialize update timer

  // --- Attach Encoder Interrupts ---
  Serial.println("Attaching Encoder Interrupts...");
  attachInterrupt(digitalPinToInterrupt(32), std::bind(&RotaryEncoder::tick, &encoder1), CHANGE);
  attachInterrupt(digitalPinToInterrupt(33), std::bind(&RotaryEncoder::tick, &encoder1), CHANGE);
  Serial.println("Interrupts Attached.");

  // --- Initial Display Drawing ---
  Serial.println("Initial screen clear...");
  tft.fillScreen(TFT_BLACK); // Clear screen once
  Serial.println("Drawing initial character...");
  drawSelections(selectedIndex); // Draw the starting image
  Serial.println("--- Setup Complete ---");
}

// --- Main Loop ---
void loop() {
  // Call tick() in loop as well - may improve robustness
  encoder1.tick();

  int currentPosition = encoder1.getPosition(); // Read latest position
  int targetIndex = abs(currentPosition) % NUM_IMAGES; // Calculate target index
  unsigned long currentTime = millis();         // Get current time
  unsigned long timeElapsed = currentTime - lastUpdateTime; // Calculate elapsed time

  // --- Check Conditions ---
  bool indexChanged = (targetIndex != selectedIndex);
  bool intervalMet = (timeElapsed >= updateInterval);

  // --- Main Rate Limiting Logic ---
  // Update display if index changed AND enough time has passed
  if (indexChanged && intervalMet) {
    Serial.print("Changing selection to: ");
    Serial.println(characterNames[targetIndex]);
    
    selectedIndex = targetIndex;      // Update the displayed index
    drawSelections(selectedIndex);    // Draw the new character
    
    // Update the time of this update
    lastUpdateTime = currentTime;
  }

  // --- Button Handling (Debounced) ---
  static unsigned long lastButtonCheckTime = 0;
  static int lastPhysicalButtonState = HIGH;
  int currentPhysicalButtonState = digitalRead(buttonPin);

  if (currentPhysicalButtonState != lastPhysicalButtonState) {
    lastButtonCheckTime = currentTime;
  }

  if ((currentTime - lastButtonCheckTime) > buttonDebounceDelay) {
    if (currentPhysicalButtonState != buttonIsPressed) {
      buttonIsPressed = currentPhysicalButtonState;
      if (buttonIsPressed == LOW) { // Button pressed (LOW)
        Serial.println("Button pressed - sending selection");
        sendSelection();
      }
    }
  }
  lastPhysicalButtonState = currentPhysicalButtonState;
}

// --- Drawing Function ---
void drawSelections(int index) {
  if (index < 0 || index >= NUM_IMAGES) {
    Serial.print("Error: Invalid index for drawing: ");
    Serial.println(index);
    return;
  }
  
  // Draw the character image
  tft.pushImage(0, 0, IMAGE_WIDTH, IMAGE_HEIGHT, imageArray[index]);
  
  // Optionally display character name at the bottom
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, IMAGE_HEIGHT - 30);
  tft.print(characterNames[index]);
}

// --- Send Selection Function ---
void sendSelection() {
  // Send the character selection in the expected format for the server
  Serial.print("Selected image index sent: ");
  Serial.println(selectedIndex);
  
  // Also send the character name for debugging
  Serial.print("Character name: ");
  Serial.println(characterNames[selectedIndex]);
} 