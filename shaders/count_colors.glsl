#version 430 core

layout(local_size_x = 8, local_size_y = 8, local_size_z = 4) in;
layout(rgba32f, binding = 0) uniform image2D imageSlice;

layout(std430, binding = 1) buffer counterBuffer
{
  uint counters[][4];
} cIn;

layout(std430, binding = 2) buffer centerBuffer
{
    vec4 c[];
} centerIn;

layout(std430, binding = 3) buffer quadVerts
{
    mat4x2 vSet[];
} quadVertsIn;

layout(std430, binding = 4) buffer quadIndices
{
    ivec4 iSet[];
}quadIndicesIn;

uniform float tool_radius;
uniform int iterations;

bool isInsideCircle(float radius, vec2 centerCoords, ivec2 pixelCoords) {
    float leftSide = pow(pixelCoords.x - centerCoords.x, 2) +
        pow(pixelCoords.y - centerCoords.y, 2);

    return (leftSide < pow(radius, 2));
}

bool isInsideQuad(ivec2 point, uint iteration) {
    int i = 0;
    ivec4 quadIndices = quadIndicesIn.iSet[iteration];
    mat4x2 quadPoints = quadVertsIn.vSet[iteration];

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
    uint currentIteration = gl_GlobalInvocationID.z;
    ivec2 imageDims = imageSize(imageSlice);

    if(
        texelPosition.x > (imageDims.x - 1) ||
        texelPosition.y > (imageDims.y - 1) ||
        currentIteration > (iterations - 1)) {

        return; //Don't go out of image bounds or iteration bounds.
    }

    vec4 circleCenters = centerIn.c[currentIteration];


    bool insideInitCirc = isInsideCircle(tool_radius, circleCenters.xy, texelPosition.yx);
    bool insideDestCirc = isInsideCircle(tool_radius, circleCenters.zw, texelPosition.yx);
    bool insideQuad =     isInsideQuad(texelPosition.yx, currentIteration);

    bool insideCutRegion = !insideInitCirc && (insideQuad || insideDestCirc);

    if (!insideCutRegion) {
        return; //No counting if we aren't in the cutting region.
    }

    vec4 texColor = imageLoad(imageSlice, texelPosition);
    if (texColor.a >= 0.98) {
        if (texColor.b >= 0.98) {
            atomicAdd(cIn.counters[currentIteration][0], 1); //Model Pixel
        } else if (texColor.r >= 0.98 && texColor.g < 0.9) {
            atomicAdd(cIn.counters[currentIteration][1], 1); //Obstacle Pixel
        } else {
            atomicAdd(cIn.counters[currentIteration][2], 1); //Stock Pixel
        }
    } else {
        atomicAdd(cIn.counters[currentIteration][3], 1); //Empty Pixel
    }

    return;
}
