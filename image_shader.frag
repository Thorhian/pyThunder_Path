#version 330

uniform sampler2D prev_render;
out vec4 outColor;

void main() {
  float xCoord = gl_FragCoord.x;
  float yCoord = gl_FragCoord.y;
  vec4 texColor = texelFetch(prev_render, ivec2(xCoord, yCoord), 0);

  if(abs(texelFetch(prev_render, ivec2(xCoord + 1, yCoord), 0).b - texColor.b) > 0.2) {
    outColor = vec4(1.0, 0.5, 0.0, 1.0);
  }
  else if(abs(texelFetch(prev_render, ivec2(xCoord, yCoord + 1), 0).b - texColor.b) > 0.2) {
    outColor = vec4(1.0, 0.5, 0.0, 1.0);
  }
  else if(abs(texelFetch(prev_render, ivec2(xCoord - 1, yCoord), 0).b - texColor.b) > 0.2) {
    outColor = vec4(1.0, 0.5, 0.0, 1.0);
  }
  else if(abs(texelFetch(prev_render, ivec2(xCoord, yCoord - 1), 0).b - texColor.b) > 0.2) {
    outColor = vec4(1.0, 0.5, 0.0, 1.0);
  }
  else {
    outColor = texColor;
  }
}
