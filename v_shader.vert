#version 330

in vec2 inVert;
in vec3 inColor;

out vec3 vColor;

void main() {
    vColor = inColor;
    gl_Position = vec4(inVert, 0.0, 1.0);
}
