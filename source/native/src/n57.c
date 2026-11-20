#define _POSIX_C_SOURCE 200809L
#include "n57.h"
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const struct n57_signal {
    const char *key;
    unsigned did, width;
    double num, den, offset, lo, hi;
} signals[] = {
#define N57_SIGNAL(key, did, width, num, den, offset, lo, hi) {key, did, width, num, den, offset, lo, hi},
#include "n57_signals.def"
#undef N57_SIGNAL
};

static const struct n57_signal *find(unsigned did) {
    unsigned i;
    for (i=0;i<sizeof signals/sizeof signals[0];i++) if (signals[i].did==did) return signals+i;
    return 0;
}

unsigned n57_parse_index(const char *text) {
    unsigned i, value=0;
    if (!text || strlen(text)!=6) return 0;
    for (i=0;i<6;i++) {
        char c=text[i];
        if (c>='0' && c<='9') value=value*16+(unsigned)(c-'0');
        else if (c>='a' && c<='f') value=value*16+(unsigned)(c-'a'+10);
        else if (c>='A' && c<='F') value=value*16+(unsigned)(c-'A'+10);
        else return 0;
    }
    return value;
}

unsigned n57_index_file(const char *path) {
    char text[7], extra;
    unsigned value=0;
    FILE *f=fopen(path,"r");
    if (!f) return 0;
    if (fscanf(f,"%6s %c",text,&extra)==1) value=n57_parse_index(text);
    fclose(f);
    return value;
}

int n57_decode(unsigned did, const unsigned char *p, size_t len, double *out) {
    const struct n57_signal *s=find(did);
    uint32_t raw=0;
    unsigned i;
    double value;
    if (!s || !p || !out || len!=s->width) return 0;
    for (i=0;i<s->width;i++) raw=(raw<<8)|p[i];
    value=raw*s->num/s->den+s->offset;
    if (!isfinite(value) || value<s->lo || value>s->hi) return 0;
    *out=value;
    return 1;
}

int n57_match(n57_exchange_fn exchange, void *ctx, unsigned expected) {
    const unsigned char req[]={0x22,0xf1,0x50}, ack[]={0x62,0xf1,0x50};
    unsigned char reply[16];
    unsigned negative, i, actual;
    int n;
    if (!expected) return 0;
    n=exchange(ctx,0x12,req,3,ack,3,reply,sizeof reply,800,&negative);
    if (n<0) return n==-2 ? 0 : n;
    if (n<6 || n>10) return 0;
    for (i=3;i<(unsigned)n-3;i++) if (reply[i]) return 0;
    actual=((unsigned)reply[n-3]<<16)|((unsigned)reply[n-2]<<8)|reply[n-1];
    return actual==expected;
}

int n57_read(n57_exchange_fn exchange, void *ctx, unsigned did, double *out) {
    const struct n57_signal *s=find(did);
    const unsigned char clear[]={0x2c,3,0xf3,3}, cleared[]={0x6c,3,0xf3,3};
    const unsigned char read[]={0x22,0xf3,3}, prefix[]={0x62,0xf3,3};
    const unsigned char defined[]={0x6c,1,0xf3,3};
    unsigned char req[]={0x2c,1,0xf3,3,0,0,1,0}, reply[32];
    unsigned negative=0;
    int n;
    if (!s) return 0;
    n=exchange(ctx,0x12,clear,4,cleared,4,reply,sizeof reply,800,&negative);
    if (n<0 && !(n==-2 && negative==0x31)) return n==-2 ? 0 : n;
    if (n>=0 && n!=4) return 0;
    req[4]=(unsigned char)(did>>8); req[5]=(unsigned char)did; req[7]=(unsigned char)s->width;
    n=exchange(ctx,0x12,req,8,defined,4,reply,sizeof reply,800,&negative);
    if (n<0) return n==-2 ? 0 : n;
    if (n!=4) return 0;
    n=exchange(ctx,0x12,read,3,prefix,3,reply,sizeof reply,800,&negative);
    if (n<0) return n==-2 ? 0 : n;
    return n>=3 && n57_decode(did,reply+3,(size_t)n-3,out);
}
