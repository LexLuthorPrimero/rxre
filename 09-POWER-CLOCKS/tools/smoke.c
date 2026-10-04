/* smoke.c -- lee un pixel del framebuffer tras un draw. ES EL ORACULO.
 * Si el valor es constante con iter crecientes, el shader esta siendo
 * optimizado y el "carga" no carga nada. No hay otra forma de saberlo. */
#define _GNU_SOURCE
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
static const char *VS="#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}\n";
static const char *FS=
"#version 300 es\n"
"precision highp float;\n"
"uniform int u_iter;\nout vec4 o;\n"
"void main(){\n"
"  vec2 c=gl_FragCoord.xy;\n"
"  float a=1.000001;\n"
"  float x=c.x*0.001+c.y*0.002;\n"
"  for(int i=0;i<u_iter;++i) x=a*x+0.5;\n"
"  o=vec4(x, x*0.5, x*0.25, 1.0);\n"   /* sin fract(): se ve el valor CRUDO */
"}\n";
int main(int argc,char**argv){
  EGLDisplay d; EGLContext c; EGLConfig g; EGLint n;
  GLuint p,v,f,vao; unsigned char px[4]; GLint loc; int it,i;
  PFNEGLGETPLATFORMDISPLAYEXTPROC gp=(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
  PFNEGLQUERYDEVICESEXTPROC qd=(PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");
  PFNEGLQUERYDEVICESTRINGEXTPROC qs=(PFNEGLQUERYDEVICESTRINGEXTPROC)eglGetProcAddress("eglQueryDeviceStringEXT");
  EGLDeviceEXT dv[8]; EGLint nd=0,el=-1;
  qd(8,dv,&nd);
  for(i=0;i<nd;i++){const char*s=qs(dv[i],0x3233); if(!s)continue; char b[128],*sl; int fd; long vv=-1;
    snprintf(b,sizeof b,"%s",s); sl=strrchr(b,'/'); if(sl)memmove(b,sl+1,strlen(sl+1)+1);
    char p2[300]; snprintf(p2,sizeof p2,"/sys/class/drm/%s/device/vendor",b); fd=open(p2,O_RDONLY);
    char t[32]={0}; if(fd>=0){int k=read(fd,t,31);close(fd); if(k>0){char*h=strstr(t,"0x"); vv=h?strtol(h,0,16):strtol(t,0,16);} }
    if(vv==0x1002&&el<0)el=i; }
  if(el<0){fprintf(stderr,"sin AMD\n");return 4;}
  d=gp(0x313F,dv[el],NULL);
  if(!eglInitialize(d,0,0)){fprintf(stderr,"init\n");return 3;}
  eglBindAPI(EGL_OPENGL_ES_API);
  eglChooseConfig(d,(EGLint[]){EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT,EGL_NONE},&g,1,&n);
  c=eglCreateContext(d,g,EGL_NO_CONTEXT,(EGLint[]){EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE});
  eglMakeCurrent(d,EGL_NO_SURFACE,EGL_NO_SURFACE,c);
  v=glCreateShader(GL_VERTEX_SHADER); glShaderSource(v,1,&VS,0); glCompileShader(v);
  f=glCreateShader(GL_FRAGMENT_SHADER); glShaderSource(f,1,&FS,0); glCompileShader(f);
  {GLint ok=0; glGetShaderiv(f,GL_COMPILE_STATUS,&ok); if(!ok){char l[512];glGetShaderInfoLog(f,512,0,l);fprintf(stderr,"%s\n",l);return 6;}}
  p=glCreateProgram(); glAttachShader(p,v); glAttachShader(p,f); glLinkProgram(p); glUseProgram(p);
  loc=glGetUniformLocation(p,"u_iter"); glGenVertexArrays(1,&vao); glBindVertexArray(vao);
  glViewport(0,0,64,64);
  printf("iter  px[0]  px[1]  px[2]   (pixel leido del framebuffer)\n");
  for(it=1;it<=4096;it*=4){
    glUniform1i(loc,it);
    glClearColor(0,0,0,1); glClear(GL_COLOR_BUFFER_BIT);
    glDrawArrays(GL_TRIANGLES,0,3); glFinish();
    memset(px,0,4); glReadPixels(32,32,1,1,GL_RGBA,GL_UNSIGNED_BYTE,px);
    printf("%5d  %5d  %5d  %5d\n",it,px[0],px[1],px[2]);
  }
  return 0;
}
