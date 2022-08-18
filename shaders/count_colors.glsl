#version 430 core

layout(local_size_x = 16, local_size_y = 16, local_size_z = 1) in;
layout(rgba32f, binding = 0) uniform image2D imageSlice;
layout(std430, binding = 1) buffer counterBuffer
{
  uint counters[];
} cIn;
uniform vec4 circleCenters;
uniform float circleRadius;
uniform mat4x2 quadPoints;
uniform ivec4   quadIndices;

bool isInsideCircle(float radius, vec2 centerCoords, ivec2 pixelCoords) {
    float leftSide = pow(pixelCoords.x - centerCoords.x, 2) +
        pow(pixelCoords.y - centerCoords.y, 2);

    return (leftSide < pow(radius, 2));
}

bool isInsideQuad(ivec2 point) {
    int i = 0;
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
    ivec2 texelPosition = ivec2(gl_GlobalInvocationID.xy);
    ivec2 imageDims = imageSize(imageSlice);

    if(texelPosition.x > (imageDims.x - 1) || texelPosition.y > (imageDims.y - 1)) {
        return;
    }

    vec4 texColor = imageLoad(imageSlice, texelPosition);

    if((texColor.a >= 0.98) &&
      (isInsideCircle(circleRadius, circleCenters.xy, texelPosition.yx) || 
      isInsideCircle(circleRadius, circleCenters.zw, texelPosition.yx) ||
      isInsideQuad(texelPosition.yx))) {
        if (texColor.b >= 0.98) {
          atomicAdd(cIn.counters[0], 1); //Model Pixel
      } else if (texColor.r >= 0.98) {
          atomicAdd(cIn.counters[1], 1); //Obstacle Pixel
      } else {
          atomicAdd(cIn.counters[2], 1); //Stock Pixel
      }
    }

    atomicAdd(cIn.counters[3], 1);//Empty Pixel
    return;
}
