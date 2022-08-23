/* # vim: ft=glsl */
#version 330

uniform sampler2D fullRender;
uniform sampler2D stockOnlyRender;

out vec4 outColor;

void main() {
  ivec2 coordinates = ivec2(gl_FragCoord.xy);
  vec4 fullRenderColor = texelFetch(fullRender, coordinates, 0);
  vec4 stockRenderColor = texelFetch(stockOnlyRender, coordinates, 0);
  vec4 newColor = vec4(0.0, 0.0, 0.0, 1.0);

  if(!(stockRenderColor.a >= 0.99) && 
    (fullRenderColor.b >= 0.99 ||
    fullRenderColor.r >= 0.99)) {

    newColor = vec4(0.0, 0.0, 0.0, 0.0);
  }

  outColor = newColor;
}

