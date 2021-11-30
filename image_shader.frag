#version 330

uniform sampler2D prev_render;
in vec2 uv;
out vec4 outColor;

void main() {
  vec4 texColor = texture(prev_render, uv);
  texColor.g = clamp(texColor.g + 0.8, 0.0, 1.0);
  outColor = texColor;
}
