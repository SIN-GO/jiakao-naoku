import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DAY,DEFAULT_INTERVALS,emptyState,cardFor,recordAnswer,dueQuestions,markStudied,makePlan,filterQuestions,validateBackup,sameAnswers,validDay} from '../web/core.mjs';
const q={id:'test-one',fingerprint:'v1',options:{A:'正确',B:'错误'},answers:['A'],vehicles:['C1'],subjects:['subject1'],topics:['law']};
const t=new Date(2026,10,13,9).getTime();
const profile={examDate:'2026-12-12',dailyMinutes:30,createdDay:'2026-11-13',subject:'subject1',vehicle:'C1'};
test('多选按集合计分，漏选不算正确',()=>{assert.ok(sameAnswers(['C','A'],['A','C']));assert.ok(!sameAnswers(['A'],['A','C']));});
test('答错10分钟到期，答对推进下一间隔',()=>{
 let s=recordAnswer(emptyState(),q,['B'],{now:t});
 assert.equal(cardFor(s,q).dueAt,t+600000);
 assert.equal(dueQuestions([q],s,t+599999).length,0);
 assert.equal(dueQuestions([q],s,t+600000).length,1);
 s=recordAnswer(s,q,['A'],{now:t+600000,mode:'review'});
 assert.equal(cardFor(s,q).stage,1);assert.equal(cardFor(s,q).dueAt,t+600000+DAY);
});
test('提前答对、普通练习答对不能跳过复习阶段',()=>{
 let s=recordAnswer(emptyState(),q,['B'],{now:t});
 s=recordAnswer(s,q,['A'],{now:t+10,mode:'review'});
 assert.equal(cardFor(s,q).stage,0);
 s=recordAnswer(s,q,['A'],{now:t+DAY,mode:'practice'});
 assert.equal(cardFor(s,q).stage,0);assert.equal(dueQuestions([q],s,t+DAY).length,1);
});
test('再次答错及不确定重置周期',()=>{
 let s=recordAnswer(emptyState(),q,['B'],{now:t});
 s=recordAnswer(s,q,['A'],{now:t+DAY,mode:'review'});
 s=recordAnswer(s,q,['A'],{now:t+DAY+1,uncertain:true});
 assert.equal(cardFor(s,q).stage,0);assert.equal(cardFor(s,q).wrongCount,2);assert.equal(cardFor(s,q).dueAt,t+DAY+1+600000);
});
test('全部间隔后才完成复习，再答错可重新激活',()=>{
 let s=recordAnswer(emptyState(),q,['B'],{now:t});
 for(let i=0;i<DEFAULT_INTERVALS.length;i++)s=recordAnswer(s,q,['A'],{now:cardFor(s,q).dueAt,mode:'review'});
 assert.equal(cardFor(s,q).mastered,true);assert.equal(dueQuestions([q],s,t+100*DAY).length,0);
 s=recordAnswer(s,q,['B'],{now:t+100*DAY});assert.equal(cardFor(s,q).mastered,false);
});
test('重复提交事件只计一次，阅读卡片不影响正确率',()=>{
 const s=recordAnswer(emptyState(),q,['B'],{now:t,eventId:'one'});
 assert.equal(recordAnswer(s,q,['B'],{now:t,eventId:'one'}).cards[q.id].attempts,1);
 const read=markStudied(markStudied(emptyState(),q,t),q,t+1);
 assert.equal(cardFor(read,q).attempts,0);assert.equal(Object.values(read.activity)[0].studied,1);
});
test('未标注车型绝不混入车型专属池',()=>{
 const unknown={...q,id:'unknown',vehicles:[]};
 assert.deepEqual(filterQuestions([q,unknown],{vehicle:'C1'}).map(x=>x.id),['test-one']);
 assert.deepEqual(filterQuestions([q,unknown],{vehicle:'unassigned'}).map(x=>x.id),['unknown']);
});
test('计划优先复习，不足预算显示积压，不伪造完成',()=>{
 const qs=Array.from({length:20},(_,i)=>({...q,id:'q-'+i}));
 let s=emptyState();for(const x of qs)s=recordAnswer(s,x,['B'],{now:t});
 const plan=makePlan(qs,s,{...profile,dailyMinutes:5},t+DAY);
 assert.equal(plan.reviewSlots,6);assert.equal(plan.reviewOverflow,14);assert.equal(plan.newTarget,0);
 assert.equal(dueQuestions(qs,s,t+DAY).length,20);
});
test('零题、过期日期、无效日期及不合理时间边界',()=>{
 assert.equal(makePlan([],emptyState(),profile,t).remaining,0);
 assert.throws(()=>makePlan([q],emptyState(),{...profile,examDate:'2026-11-12'},t));
 assert.throws(()=>makePlan([q],emptyState(),{...profile,examDate:'2026-02-31'},t));
 assert.throws(()=>makePlan([q],emptyState(),{...profile,dailyMinutes:0},t));
 assert.equal(validDay('2028-02-29'),true);assert.equal(validDay('2026-02-29'),false);
});
test('预算不足给出提示，题目更新后旧掌握度不复用',()=>{
 const qs=Array.from({length:2000},(_,i)=>({...q,id:'q-'+i}));
 assert.ok(makePlan(qs,emptyState(),{...profile,dailyMinutes:5},t).capacityWarning);
 const s=recordAnswer(emptyState(),q,['B'],{now:t});
 assert.equal(cardFor(s,{...q,fingerprint:'v2'}).attempts,0);
});
test('备份可恢复进度，未知题或变更题跳过，畸形备份拒绝',()=>{
 let s=recordAnswer(emptyState(),q,['B'],{now:t});s.profile=profile;
  s.milestones.practical2=true;s.milestoneDates.practical3='2026-12-01';
  const restored=validateBackup(s,[q]);assert.equal(restored.milestones.practical2,true);assert.equal(restored.milestoneDates.practical3,'2026-12-01');
 assert.equal(validateBackup(s,[q]).cards[q.id].wrongCount,1);
 assert.equal(Object.keys(validateBackup(s,[{...q,fingerprint:'v2'}]).cards).length,0);
 s.cards[q.id].dueAt=null;assert.throws(()=>validateBackup(s,[q]));
});
