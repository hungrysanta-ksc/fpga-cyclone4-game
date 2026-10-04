// Convert the MiSTer-style active-high button vector into the active-low
// four-bit matrix read by the Game Boy FF00/P1 register.
// joystick[7:0] = Start,Select,B,A,Up,Down,Left,Right.
module gbc_joypad(
 input wire[7:0]joystick,input wire[1:0]p54,output wire[3:0]joy_din
);
 wire[3:0]directions=~{joystick[2],joystick[3],joystick[1],joystick[0]}|{4{p54[0]}};
 wire[3:0]buttons=~{joystick[7],joystick[6],joystick[5],joystick[4]}|{4{p54[1]}};
 assign joy_din=directions&buttons;
endmodule
