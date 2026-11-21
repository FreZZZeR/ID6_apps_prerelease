#define _POSIX_C_SOURCE 200809L
#include "hud_sample.h"
#include "diag_link.h"
#include "gauge_core.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static int native, bad_index, bad_gear, bad_egs, bad_display, bad_button, bad_rpm, no_baro, clears, definitions, reads, calls;
static unsigned did, speed_raw;

int diag_hsfz_connect(const char *host, unsigned port) {
    assert(!strcmp(host,"model") && port==6801);
    return socket(AF_INET,SOCK_STREAM,0);
}

int diag_hsfz_exchange(int fd, unsigned ecu, const unsigned char *q, unsigned n,
                       const unsigned char *prefix, unsigned pn, unsigned char *r,
                       unsigned cap, unsigned timeout, unsigned *negative) {
    (void)fd; (void)cap; (void)timeout;
    calls++;
    assert(ecu==0x12 || ecu==0x18);
    memcpy(r,prefix,pn);
    if (n==3 && !memcmp(q,"\x22\xda\x2e",3)) {
        assert(ecu==0x18 && !native); r[3]=0; r[4]=bad_gear ? 5 : 6; return 5;
    }
    if (native) {
        assert(q[0]!=1); /* A configured N57 must never fall back to mode 01. */
        if (ecu==0x18) {
            if (n==3 && !memcmp(q,"\x22\xf1\x50",3)) {
                memcpy(r+3,bad_egs ? "\x04\x05\x06" : "\x0f\x14\xb0",3); return 6;
            }
            if (n==3 && !memcmp(q,"\x22\x43\x06",3)) { r[3]=bad_gear ? 5 : 8; return 4; }
            assert(n==3 && !memcmp(q,"\x22\xda\x27",3));
            memcpy(r+3,"\x00\x01\x00\x00\x00\x00",6);
            if (bad_display) r[4]=3;
            if (bad_button) r[8]=2;
            return 9;
        }
        if (n==3 && !memcmp(q,"\x22\xf1\x50",3)) {
            memcpy(r+3,bad_index ? "\x04\x05\x06" : "\x01\x02\x03",3); return 6;
        }
        if (n==4 && !memcmp(q,"\x2c\x03\xf3\x03",4)) { clears++; did=0; return 4; }
        if (n==8 && !memcmp(q,"\x2c\x01\xf3\x03",4)) {
            assert(!did && q[6]==1 && q[7]==2);
            definitions++; did=((unsigned)q[4]<<8)|q[5]; return 4;
        }
        if (n==3 && !memcmp(q,"\x22\xf3\x03",3)) {
            unsigned raw;
            reads++;
            if (did==0x5955) raw=bad_rpm ? 65535 : 1600;
            else if (did==0x4c14) raw=speed_raw;
            else if (did==0x4841) raw=25122;
            else { assert(did==0x4cf0); raw=32768; if (no_baro) { *negative=0x31; return -2; } }
            r[3]=(unsigned char)(raw>>8); r[4]=(unsigned char)raw; return 5;
        }
    } else {
        if (n==2 && q[0]==1 && q[1]==0x0c) { r[2]=0x0c; r[3]=0x80; return 4; }
        if (n==2 && q[0]==1 && q[1]==0x0d) { r[2]=(unsigned char)speed_raw; return 3; }
        if (n==3 && q[0]==0x22 && q[1]==0x42) {
            unsigned raw=q[2]==5 ? 32000 : 25600;
            r[3]=(unsigned char)(raw>>8); r[4]=(unsigned char)raw; return 5;
        }
    }
    assert(!"Unexpected HUD diagnostic request");
    return -1;
}

static int poll_case(hud_sample *sample, int park) {
    hud_reader r;
    hud_reader_init(&r);
    r.n57_index=native ? 0x010203 : 0; r.config_error=0;
    int result=hud_reader_poll(&r,"model",sample,park);
    hud_reader_close(&r);
    assert(r.fd==-1 && r.lock==-1);
    return result;
}

int main(void) {
    hud_sample sample;
    native=1;
    assert(poll_case(&sample,1)==1 && sample.rpm==800 && sample.gear=='P' && sample.n57);
    assert(sample.have_boost && sample.boost_tenths==189 && sample.rpm_ms<=bd_mono_ms());
    assert(hud_boost_fresh(&sample,sample.boost_ms+1199) && !hud_boost_fresh(&sample,sample.boost_ms+1200));
    assert(clears==4 && definitions==4 && reads==4);
    speed_raw=1; assert(poll_case(&sample,1)==-1); speed_raw=0;
    bad_gear=1; assert(poll_case(&sample,1)==-1); bad_gear=0;
    bad_egs=1; assert(poll_case(&sample,1)==-1); bad_egs=0;
    bad_display=1; assert(poll_case(&sample,1)==-1); bad_display=0;
    bad_button=1; assert(poll_case(&sample,1)==-1); bad_button=0;
    bad_index=1; assert(poll_case(&sample,0)==-1); bad_index=0;
    bad_rpm=1; assert(poll_case(&sample,0)==-1); bad_rpm=0;
    no_baro=1; assert(poll_case(&sample,0)==1 && !sample.have_boost); no_baro=0;
    native=0;
    assert(poll_case(&sample,1)==1 && sample.rpm==800 && !sample.n57 && sample.boost_tenths==218);
    speed_raw=1; assert(poll_case(&sample,1)==-1);
    { hud_reader r; int before=calls; hud_reader_init(&r); r.config_error=1;
      assert(hud_reader_poll(&r,"model",&sample,0)==-1 && calls==before); hud_reader_close(&r); }
    puts("HUD reader: N57 DDE RPM/boost, exact standstill/Park, identity, failures and gasoline regression OK");
    return 0;
}
