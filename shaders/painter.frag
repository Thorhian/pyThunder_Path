/* # vim: ft=glsl */
#version 330 core

uniform sampler2D prev_render;
uniform vec4 circleCenters;
uniform float circleRadius;
uniform mat4x2 quadPoints;
uniform ivec4 quadIndices;
out vec4 outColor;

bool isInsideCircle(float radius, vec2 centerCoords, ivec2 pixelCoords) {
    float leftSide = pow(pixelCoords.x - centerCoords.x, 2) +
        pow(pixelCoords.y - centerCoords.y, 2);

    return (leftSide < pow(radius, 2));
}

bool isInsideQuad(ivec2 point) { int i = 0;
    while(i < 4) {
        int trueIndice = quadIndices[i];
        int nextTrue = quadIndices[(i + 1) % 4];
        vec2 v1 = quadPoints[trueIndice];
        vec2 v2 = quadPoints[nextTrue];
        float d = ((v2.x - v1.x) * (point.y - v1.y)) - ((point.x - v1.x) * (v2.y - v1.y));

        if(d < 0) {
            return false;
        }

        i += 1;
    }

    return true;
}

void main() {
  ivec2 pixelCoords = ivec2(gl_FragCoord.xy);
  vec4 texColor = texelFetch(prev_render, pixelCoords, 0);
  vec4 newColor = texColor;

  if(isInsideCircle(circleRadius, circleCenters.xy, pixelCoords.yx) ||
    isInsideCircle(circleRadius, circleCenters.zw, pixelCoords.yx) ||
    isInsideQuad(pixelCoords.yx)) {
      newColor.a = 0.0;
    }

  outColor = newColor;
}
