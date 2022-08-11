#version 330

uniform sampler2D prev_render;
out vec4 outcolor;

void main() {
  float xCoord = gl_FragCoord.x;
  float yCoord = gl_FragCoord.y;
  vec4 texColor = texelFetch(prev_render, ivec2(xCoord, yCoord), 0);

}
