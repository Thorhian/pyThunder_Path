#version 330

in vec3 in_vert;
in vec4 in_color;

out vec4 v_color;

uniform mat4 projectionMatrix;
uniform mat4 viewMatrix;


void main() {
  v_color = in_color;
  gl_Position = projectionMatrix * viewMatrix * vec4(in_vert, 1.0);
}
