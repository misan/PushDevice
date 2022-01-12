
#include <Encoder.h>

// Change these two numbers to the pins connected to your encoder.
//   Best Performance: both pins have interrupt capability
//   Good Performance: only the first pin has interrupt capability
//   Low Performance:  neither pin has interrupt capability
Encoder myEnc(A4, A5);

long oldPosition  = 0;

#include <HX711.h>

// HX711.DOUT - pin #A1
// HX711.PD_SCK - pin #A0
const int LOADCELL_DOUT_PIN = A1;
const int LOADCELL_SCK_PIN = A0;

HX711 scale;

float force;
int i=0;

float F=20; // max force in newtons
float L=30; // max elongation in mm

/* for CNC-Shield */

#define ENABLE 8
#define XEND  9
#define XDIR  5
#define XSTEP 2




void setup() {
  // put your setup code here, to run once:
  pinMode(ENABLE, OUTPUT); digitalWrite(ENABLE,HIGH); 
  pinMode(XEND, INPUT_PULLUP); 
  pinMode(XDIR, OUTPUT); digitalWrite(XDIR,LOW); //backwards=LOW
  pinMode(XSTEP, OUTPUT); digitalWrite(XSTEP,LOW);

  Serial.begin(115200);
  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN); //put your setup code here, to run once:
  scale.set_scale(90047.6);
  scale.tare();
  Serial.println("");
  Serial.println("ready");
}

int s=0;
void step() {
  for(s=0;s<16;s++) {
  digitalWrite(XSTEP,HIGH);
  delayMicroseconds(10);
  digitalWrite(XSTEP,LOW);
  delayMicroseconds(500);
  }
}

void forward() { digitalWrite(XDIR,HIGH); }
void backward() { digitalWrite(XDIR,LOW); }
void disableMotor() { digitalWrite(ENABLE,HIGH); }
void enableMotor() { digitalWrite(ENABLE,LOW); }
void resetCell() { scale.tare(); }
void manualMeasurement() {
    force=scale.get_units(5);
    Serial.print("Manual");
    Serial.print("\t");
    Serial.print(force);
    Serial.println("\tN");
}

// ***** THIS IS THE MANUAL TEST
void push_test_manual(float F, float L) { // start pushing till a certain force on the load cell
  // is reached, then stop for 10 seconds, then move back to the 
  // original location and stop forever
  disableMotor(); // just in case
  myEnc.write(0); // set initial count here
  oldPosition=11;
  long newPosition;
  // start motion
  float dist;
  while(true) {
    // step();
    newPosition=myEnc.read();
    dist = newPosition*0.04; // adjust this number when you know the right one
    if(oldPosition != newPosition) {
      oldPosition = newPosition; 
      force=scale.get_units(1);
      Serial.print(dist); //pitch 8 mm/rev and 200 steps/rev == 0.04 mm/step
      Serial.print("\t");
      Serial.println(force);
      //Serial.println(" N");
    }
    if(force>F) break;
    if(dist>=L) break; // that is the max force or max elongation allowed
    if(Serial.available()>0) break; // if received anything over serial then abort
  }
  Serial.println("."); // signals the end of the process
}



// ***** USE THE MOTOR FOR THIS TEST
void push_test(float F, float L) { // start pushing till a certain force on the load cell
  // is reached, then stop for 10 seconds, then move back to the 
  // original location and stop forever
  enableMotor();
  forward();
  // start motion
  float dist;
  for(i=0; i<2000; i++) { // 80 mm
    step();
    dist = (i+1)*0.04;
    force=scale.get_units(1);
    Serial.print(dist); //pitch 8 mm/rev and 200 steps/rev == 0.04 mm/step
    Serial.print("\t");
    Serial.println(force);
    //Serial.println(" N");
    if(force>F || dist>=L) break; // that is the max force or max elongation allowed
    if(Serial.available()>0)  break; // if received anything over serial then abort
  }
  Serial.println("."); // signals the end of the process
  //max push force reached
  // delay(1000);
  // now go back to initial position
  backward();
  for(;i>0; i--) step();
  disableMotor();
}

void process_line() {
  char cmd = Serial.read();
  if (cmd > 'Z') cmd -= 32;
  switch (cmd) {
    case 'R': resetCell(); break;
    case 'X': break;
    case '?': manualMeasurement(); break;
    case 'S': delay(10); while(Serial.available()>0) Serial.read(); push_test(F,L); break;
    case 'L': L = Serial.parseFloat(); L=min(60,L); Serial.print(L); Serial.println(" mm"); break;  // max 60 mm elongation
    case 'F': F = Serial.parseFloat(); F=min(50,F); Serial.print(F); Serial.println(" N"); break;  // max 50 N force
    case 'M': delay(20); while(Serial.available()>0) Serial.read(); push_test_manual(F,L); break;
  }
  if(Serial.available()>0) while (Serial.read() != 10); // dump extra characters till LF is seen (you can use CRLF or just LF)
}

void loop() {
   if (Serial.available()) process_line();
}
