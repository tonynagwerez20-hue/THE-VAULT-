#ifndef AMIGO_NEWS_POLICY_MQH
#define AMIGO_NEWS_POLICY_MQH
#include <Contracts header.mqh>
// Experimental post-release admission, not a surprise-direction strategy.
// Existing closed-bar strategies, sessions, spread and risk checks still apply.
bool AmigoNewsAdmission(const ExternalContext &ctx,const int mode,
                        const datetime now,const int max_age_seconds,string &reason)
{
   reason="";
   if(mode==0) return true;
   if(mode<0 || mode>3) { reason="NEWS_MODE_UNSUPPORTED"; return false; }
   if(now<=0 || max_age_seconds<=0 || !ctx.news_valid ||
      ctx.news_observed_ts<=0 || ctx.news_observed_ts>now ||
      now-ctx.news_observed_ts>max_age_seconds || ctx.news_event_ts<0 ||
      (ctx.news_released && (ctx.news_event_ts<=0 || ctx.news_event_ts>ctx.news_observed_ts)))
   { reason="NEWS_UNAVAILABLE_OR_STALE"; return false; }
   if(mode==1)
   {
      if(ctx.news_active_window) { reason="NEWS_ACTIVE_WINDOW"; return false; }
      return true;
   }
   if(!ctx.news_active_window && ctx.news_event_ts==0 && !ctx.news_released)
   {
      if(mode==3) return true;
      reason="NEWS_NO_RELEASE_SETUP"; return false;
   }
   if(!ctx.news_released || ctx.news_event_ts<=0 ||
      !MathIsValidNumber(ctx.news_surprise) || !MathIsValidNumber(ctx.news_relative_surprise))
   { reason="NEWS_RELEASE_UNCONFIRMED"; return false; }
   long elapsed=(long)(now-ctx.news_event_ts);
   // Require the observation itself to have reached the settling boundary.
   if(elapsed<60 || ctx.news_observed_ts-ctx.news_event_ts<60)
   { reason="NEWS_SETTLING"; return false; }
   if(elapsed>14400) { reason="NEWS_REACTION_EXPIRED"; return false; }
   reason="NEWS_POST_RELEASE_SETUP_REQUIRED";
   return true;
}
// Final gate after automatic horizon selection, before geometry/risk/commit.
// Windows are engineering defaults requiring chronological cost-aware validation.
bool AmigoNewsHorizonAllows(const ExternalContext &ctx,const int mode,
                           const ENUM_HORIZON horizon,const datetime now,
                           const int max_age_seconds,string &reason)
{
   if(!AmigoNewsAdmission(ctx,mode,now,max_age_seconds,reason)) return false;
   if(mode==0 || mode==1) return true;
   if(mode==3 && !ctx.news_active_window && ctx.news_event_ts==0 && !ctx.news_released)
      return true;
   long minimum=0,maximum=0;
   if(horizon==HORIZON_SCALPING) { minimum=60; maximum=300; }
   else if(horizon==HORIZON_INTRADAY) { minimum=300; maximum=3600; }
   else if(horizon==HORIZON_SWING) { minimum=3600; maximum=14400; }
   else { reason="NEWS_HORIZON_INVALID"; return false; }
   long elapsed=(long)(now-ctx.news_event_ts);
   if(elapsed<minimum || ctx.news_observed_ts-ctx.news_event_ts<minimum)
   { reason="NEWS_HORIZON_SETTLING"; return false; }
   if(elapsed>maximum) { reason="NEWS_HORIZON_EXPIRED"; return false; }
   reason="NEWS_HORIZON_SETUP_REQUIRED";
   return true;
}
#endif
