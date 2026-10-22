/* SPDX-License-Identifier: MIT
 * A map slot is only a hint. Retained tag, current exact key and target-bank
 * residency are checked independently before reusing a complete ordinary row.
 */
bool nes_resident287_can(const struct nes_resident211 *s,const struct nes_native_video165 *v,unsigned slot,unsigned tag){
 if(s->fault||!s->open||s->prepared||slot==0||slot>=s->bg_slots||s->bg[slot]!=tag)return false;
 return !bit(s->used,slot)||v->bg_keys[slot]==(tag|UINT64_C(0x1fed6c8da4480000));
}
bool nes_resident287_touch(struct nes_resident211 *s,struct nes_native_video165 *v,unsigned slot,struct nes_plan191 *q){
 if(q->generation!=s->generation||!nes_resident287_can(s,v,slot,q->tag))return false;
 if(bit(s->used,slot))return true;
 remove221(s,slot,q->tag);set(s->used,slot);
 v->bg_keys[slot]=q->tag|UINT64_C(0x1fed6c8da4480000);
 if(v->bg_count<=slot)v->bg_count=(uint16_t)(slot+1);
 insert221(s,slot,v->bg_keys[slot],true);
 if(bit(s->resident[s->target],slot)){s->hits++;return true;}
 q->slot=(uint16_t)slot;
 if(!s->write(s->ctx,s->target,q)){nes_resident211_abort(s);return false;}
 set(s->dirty,slot);s->writes++;return true;
}
