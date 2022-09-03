#version 430 core

layout(local_size_x = 16, local_size_y = 16, local_size_z = 1) in;
layout(rgba32f, binding = 0) uniform image2D imageSlice;
layout(std430, binding = 1) buffer counterBuffer
{
  uint counters[];
} cIn;

void main() {
  ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
  ivec2 imageDims = imageSize(imageSlice);

  if(texelPosition.x > (imageDims.x - 1) || texelPosition.y > (imageDims.y - 1)) {
    return;
  }

  vec4 imgColor  = imageLoad(imageSlice);

}
