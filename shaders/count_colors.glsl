#version 430 core

layout(local_size_x = 16, local_size_y = 16, local_size_z = 1) in;
layout(rgba32f, binding = 0) uniform image2D imageSlice;
layout(binding = 1) uniform atomic_uint stock;
layout(binding = 1) uniform atomic_uint obstacle;
layout(binding = 1) uniform atomic_uint model;
uniform vec2 imageSize;
uniform vec4 circleCenters;
uniform float circleRadius;
uniform mat2x4 quadPouints; //Must be sorted in anti-clockwise order.

bool isInsideCircle(float radius, vec2 centerCoords, ivec2 pixelCoords) {
    float leftSide = pow(pixelCoords[0] - centerCoords[0], 2) +
        pow(pixelCoords[1] - centerCoords[1], 2);

    return (leftSide < pow(radius, 2));
}

bool isInsideQuad(mat2x4 points, ivec2 point) {
    int i = 0;
    while(i < 4) {
        vec2 v1 = points[i];
        vec2 v2 = points[(i + 1) % 4];
        d = (v2[0] - v1[0]) * (point[1] - v1[1]) - (point[0] - v1[0]) * (v2[1] - v1[1]);

        if(d < 0) {
            return false;
        }

        i += 1;
    }

    return true;
}

void main() {
    ivec2 texelPosition = ivec2(gl_GlobalInvocationID.xy);

    if(texelPosition.x > imageSize.x || texelPosition.y > imageSize.y) {
        return;
    }


    vec4 texColor = texelFetch(imageSlice, texelPosition, 0);

    if((texColor.a >= 0.98) &&
      isInsideCircle(circleRadius, vec2(circleCenters[0], circleCenters[1]), texelPosition) &&
      isInsideCircle(circleRadius, vec2(circleCenters[2], circleCenters[3]), texelPosition) &&
      isInsideQuad(quadPoints, texelPosition)) {
        if (texColor.b >= 0.98) {
          atomicCounterIncrement(model);
          return;
      } else if (texColor.r >= 0.98) {
          atomicCounterIncrement(obstacle);
          return;
      } else {
          atomicCounterIncrement(stock);
      }
    }

}
