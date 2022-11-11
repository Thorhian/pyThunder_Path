#version 450 core

layout(local_size_x = 16, local_size_y = 16, local_size_z = 1) in;
layout(rgba32f, binding = 0) uniform sampler2D imageSlice;
layout(rgba32f, binding = 2) uniform sampler2D mask;
layout(std430, binding = 1) buffer counterBuffer
{
  uint counters[];
} cIn;

uniform vec4 color1 = vec4(0.0, 0.0, 0.0, 1.0);
uniform vec4 color2 = vec4(0.0, 0.0, 1.0, 1.0);
uniform vec4 color3 = vec4(0.0, 1.0, 0.0, 1.0);

bool compareVecs(vec4 vecA, vec4 vecB, float thresh) {
  vec4 comparator = abs(vecA - vecB);
  bool withinThresh = true;

  int i = 0;
  for(i = 0; i < 4; i++) {
    if (comparator[i] > thresh) {
      withinThresh = false;
    }
  }

  return withinThresh;
}

void main() {
    ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
    ivec2 imageDims = imageSize(imageSlice);

    if(texelPosition.x > (imageDims.x - 1) || texelPosition.y > (imageDims.y - 1)) {
        return;
    }

    vec4 texColor = texelFetch(imageSlice, pos, 0);

    if (compareVecs(texColor, color1, 0.2)) {
        atomicAdd(cIn.counters[0], 1);
    }

    if (compareVecs(texColor, color2, 0.2)) {
        atomicAdd(cIn.counters[1], 1);
    }

    if (compareVecs(texColor, color3, 0.2)) {
        atomicAdd(cIn.counters[2], 1);
    }

    atomicAdd(cIn.counters[3], 1); //Total Pixels
}
