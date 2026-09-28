from pathlib import Path
import re, json, hashlib
from copy import deepcopy
from lxml import etree
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / '论文成果'
OUT.mkdir(exist_ok=True)
ASSETS = ROOT / 'assets'
ASSETS.mkdir(exist_ok=True)
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.top_margin = sec.bottom_margin = Cm(2.3)
sec.left_margin = sec.right_margin = Cm(2.4)
sec.header_distance = sec.footer_distance = Cm(1.1)

def font_style(st, size, east='宋体', bold=False):
    st.font.name = 'Times New Roman'
    st.font.size = Pt(size)
    st.font.bold = bold
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), east)

font_style(doc.styles['Normal'], 10.5)
n = doc.styles['Normal'].paragraph_format
n.line_spacing = 1.3
n.space_after = Pt(4)
n.first_line_indent = Pt(21)
n.widow_control = True
font_style(doc.styles['Title'], 17, '黑体', True)
for name,size in [('Heading 1',13),('Heading 2',11.5),('Heading 3',10.5)]:
    font_style(doc.styles[name],size,'黑体',True)
    f=doc.styles[name].paragraph_format
    f.space_before=Pt(10 if name=='Heading 1' else 7)
    f.space_after=Pt(4)
    f.keep_with_next=True
    f.first_line_indent=Pt(0)
font_style(doc.styles['Caption'],9)
doc.styles['Caption'].paragraph_format.first_line_indent=Pt(0)
doc.styles['Caption'].paragraph_format.space_after=Pt(5)
doc.core_properties.title='基于目标检测与时序证据链的烟头乱扔行为监测系统设计与实现'
doc.core_properties.subject='目标检测与时序证据链监测论文整合稿'
doc.core_properties.author=''
doc.core_properties.keywords='烟头乱扔;YOLOv8n;状态机;ByteTrack;证据链'

citations=[]
def para(text, style=None, indent=True):
    p=doc.add_paragraph(style=style)
    if not indent:p.paragraph_format.first_line_indent=Pt(0)
    for part in re.split(r'(\[\d+\]|[A-Za-zΔθτq̄]+_[A-Za-z0-9,ₜ]+⁰?)',text):
        if not part:continue
        if '_' in part and re.fullmatch(r'[A-Za-zΔθτq̄]+_[A-Za-z0-9,ₜ]+⁰?',part):
            base,idx=part.split('_',1)
            node=ss(base,idx[:-1],'0') if idx.endswith('⁰') else sub(base,idx)
            p._p.append(el('oMath',[node]))
            continue
        r=p.add_run(part)
        if re.fullmatch(r'\[\d+\]',part):
            r.font.superscript=True
            r.font.size=Pt(8)
            citations.append(int(part[1:-1]))
    return p
def h(text,level=1):doc.add_heading(text,level=level)

# Structured native Office Math. Fractions, radicals and indices remain editable.
def el(tag,children=(),**attrs):
    e=OxmlElement('m:'+tag)
    for k,v in attrs.items():e.set(qn('m:'+k),str(v))
    for c in children:e.append(deepcopy(c))
    return e
def mr(t):
    r=el('r'); te=el('t');te.text=t;r.append(te);return r
def seq(*items):
    ans=[]
    for x in items:
        if isinstance(x,list):ans.extend(x)
        elif isinstance(x,str):ans.append(mr(x))
        else:ans.append(x)
    return ans
def sub(base,index):return el('sSub',[el('e',seq(base)),el('sub',seq(index))])
def sup(base,index):return el('sSup',[el('e',seq(base)),el('sup',seq(index))])
def ss(base,lo,hi):return el('sSubSup',[el('e',seq(base)),el('sub',seq(lo)),el('sup',seq(hi))])
def frac(a,b):return el('f',[el('num',seq(a)),el('den',seq(b))])
def root(a):return el('rad',[el('radPr',[el('degHide',val='1')]),el('deg'),el('e',seq(a))])
def eq(items,num):
    p=doc.add_paragraph()
    pf=p.paragraph_format
    pf.first_line_indent=Pt(0)
    pf.space_before=Pt(4);pf.space_after=Pt(5)
    pf.keep_together=True
    pf.tab_stops.add_tab_stop(Cm(8.1),WD_TAB_ALIGNMENT.CENTER)
    pf.tab_stops.add_tab_stop(Cm(16.2),WD_TAB_ALIGNMENT.RIGHT)
    p.add_run('\t')
    p._p.append(el('oMath',seq(items)))
    p.add_run('\t（'+str(num)+'）')

def table(title,headers,rows,widths=None):
    cap=para(title,'Caption',False);cap.alignment=WD_ALIGN_PARAGRAPH.CENTER;cap.paragraph_format.keep_with_next=True
    tb=doc.add_table(rows=1,cols=len(headers))
    tb.alignment=WD_TABLE_ALIGNMENT.CENTER
    tb.autofit=False
    if widths is None:widths=[16.2/len(headers)]*len(headers)
    for col,w in zip(tb.columns,widths):col.width=Cm(w)
    for i,x in enumerate(headers):tb.rows[0].cells[i].text=x
    for row in rows:
        cells=tb.add_row().cells
        for i,x in enumerate(row):cells[i].text=str(x)
    for ri,row in enumerate(tb.rows):
        trpr=row._tr.get_or_add_trPr()
        trpr.append(OxmlElement('w:cantSplit'))
        if ri==0:trpr.append(OxmlElement('w:tblHeader'))
        for ci,cell in enumerate(row.cells):
            cell.width=Cm(widths[ci]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr=cell._tc.get_or_add_tcPr()
            borders=OxmlElement('w:tcBorders')
            for side in ['top','bottom','left','right']:
                b=OxmlElement('w:'+side);b.set(qn('w:val'),'single');b.set(qn('w:sz'),'4');b.set(qn('w:color'),'D9D9D9');borders.append(b)
            pr.append(borders)
            if ri==0:
                sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E9EDF1');pr.append(sh)
            for p in cell.paragraphs:
                p.paragraph_format.first_line_indent=Pt(0)
                p.paragraph_format.space_before=Pt(3);p.paragraph_format.space_after=Pt(3)
                p.paragraph_format.line_spacing=1.1
                p.alignment=WD_ALIGN_PARAGRAPH.CENTER if len(headers)>3 else WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs:r.font.size=Pt(9);r.font.bold=ri==0
    doc.add_paragraph().paragraph_format.space_after=Pt(0)
    return tb

def draw_flow(path,state=False):
    im=Image.new('RGB',(2100,630 if not state else 400),'white');d=ImageDraw.Draw(im)
    f=ImageFont.truetype('C:/Windows/Fonts/simsun.ttc',35)
    small=ImageFont.truetype('C:/Windows/Fonts/simsun.ttc',29)
    def box(x,y,w,hh,txt):
        d.rounded_rectangle((x,y,x+w,y+hh),radius=10,fill='#f1f3f5',outline='black',width=3)
        lines=txt.split('\n')
        for j,line in enumerate(lines):
            bb=d.textbbox((0,0),line,font=f);d.text((x+(w-(bb[2]-bb[0]))/2,y+(hh-len(lines)*45)/2+j*45),line,font=f,fill='black')
    def arrow(points):
        d.line(points,fill='black',width=4)
        x,y=points[-1];px,py=points[-2]
        if x>px:tri=[(x,y),(x-15,y-9),(x-15,y+9)]
        elif x<px:tri=[(x,y),(x+15,y-9),(x+15,y+9)]
        elif y>py:tri=[(x,y),(x-9,y-15),(x+9,y-15)]
        else:tri=[(x,y),(x-9,y+15),(x+9,y+15)]
        d.polygon(tri,fill='black')
    if not state:
        labels=['视频输入','YOLO检测','行人跟踪\n人—物关联','运动分析\n状态更新','候选事件']
        xs=[35,460,885,1310,1735]
        for x,t in zip(xs,labels):box(x,50,330,130,t)
        for x in xs[:-1]:arrow([(x+330,115),(x+425,115)])
        box(70,355,440,130,'原始视频环形缓存');arrow([(200,180),(200,355)])
        box(780,355,480,130,'关键帧与前后视频采集')
        box(1540,355,480,130,'后端校验、归档与展示')
        arrow([(510,420),(780,420)]);arrow([(1260,420),(1540,420)])
        arrow([(1900,180),(1900,255),(1020,255),(1020,355)])
        d.text((1100,266),'事件触发',font=small,fill='black')
        d.text((55,555),'处理路径与证据缓存并行；证据编码和上传采用异步任务。',font=small,fill='black')
    else:
        xs=[35,550,1065,1580]
        labels=['空闲\nIDLE','持烟\nHOLDING','抛掷\nTHROWING','落地\nLANDED']
        for x,t in zip(xs,labels):box(x,65,430,130,t)
        for x in xs[:-1]:arrow([(x+430,130),(x+515,130)])
        for x,t in [(180,'持烟持续成立'),(715,'离手且运动一致'),(1260,'地面区域内稳定')]:d.text((x,220),t,font=small,fill='black')
        d.text((100,315),'缺失或冲突：保留不确定记录；超时：终止候选；三阶段完整：输出事件。',font=small,fill='black')
    im.save(path,dpi=(300,300))
def fig(path,caption):
    p=doc.add_paragraph();p.paragraph_format.first_line_indent=Pt(0);p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.keep_with_next=True
    p.add_run().add_picture(str(path),width=Cm(16.1))
    p=para(caption,'Caption',False);p.alignment=WD_ALIGN_PARAGRAPH.CENTER

title=para('基于目标检测与时序证据链的\n烟头乱扔行为监测系统设计与实现','Title',False)
title.alignment=WD_ALIGN_PARAGRAPH.CENTER
title.paragraph_format.space_after=Pt(12)
para('摘要：针对公共场所烟头乱扔事件难以由单帧检测确认和追溯的问题，设计目标检测与时序证据链相结合的监测系统。以YOLOv8n识别香烟、手部和行人，结合行人跟踪、人—物关联及“持烟—抛掷—落地”状态机组织事件证据，并设计视频归档与后端查询流程。已有验证记录显示，模型在1139张图像上的mAP50为84.4%，mAP50–95为52.4%，香烟类别mAP50为82.2%。结果支持三类目标检测的基础可行性；完整行为识别、行人关联及系统实时性尚需独立视频实验验证。',indent=False)
para('关键词：烟头乱扔；目标检测；YOLOv8n；时序证据链；行人跟踪',indent=False)

h('1 引言')
para('烟头乱扔治理涉及垃圾发现、行为识别与事件追溯。Slaughter等通过鱼类急性毒性试验发现，烟头浸出液可对所测试的淡水及海水鱼类产生毒性，提示废弃烟头具有环境风险[1]。对校园道路、建筑出入口等场所而言，发现地面烟头只能反映遗留状态，不能直接还原丢弃过程。监测系统还需回答事件何时发生、与哪条行人轨迹相关，以及对应视频能否复核。')
para('YOLO将目标类别和位置预测统一到单次网络计算中，为视频目标检测提供了高效框架[2]。但检测到香烟不等于识别出乱扔：手边目标消失可能来自离手运动，也可能来自遮挡或漏检；地面出现烟头，也可能是此前遗留。烟头尺度小、离手运动短暂和多人交互等因素，使类别与位置之外的时序约束成为必要条件。')
para('本文围绕YOLOv8n目标检测、行人跟踪和三段式状态机设计监测系统，研究香烟—手部—行人的关联、行为阶段转换及视频证据组织方法。系统将目标位置、轨迹和关键帧组织为可追溯事件，为人工复核与清理处置提供依据。本文报告已获得的图像检测结果，并给出后续视频级验证方案，区分检测能力与完整行为判断能力。')

h('2 相关工作')
h('2.1 小目标检测与烟头识别',2)
para('小目标检测面临空间细节不足和背景干扰。Lin等提出特征金字塔网络，通过自顶向下路径与横向连接融合不同层级特征，为多尺度检测提供了基础[3]。Woo等提出卷积块注意力模块，从通道和空间两个维度对特征加权，以增强有效信息表达[4]。在香烟检测中，Wang等提出YOLOv8-MNC，将小目标检测层、注意力及上采样改进用于吸烟场景，改善了其数据集上的检测性能[5]。这些方法主要解决识别与定位，应用到乱扔判断时仍需建立跨帧关系。')
h('2.2 行为时序分析与抛掷动作识别',2)
para('垃圾丢弃识别需要描述人与物体的动态关系。Bae等通过多任务学习联合分析人体姿态、携带物体及动作状态，刻画从携带到丢弃的过程[6]。Kondratyuk等提出MoViNets，利用流式缓冲等机制降低视频识别的计算和内存开销[7]。Alharbi等将MoViNet视频分类与YOLOv8目标检测结合，构建公共场所乱扔监测系统[8]。对于烟头场景，还需将动作变化与微小物体对应：手部摆动不能单独证明抛掷，目标消失也不能替代落地观测。因此，本文采用阶段条件明确的时序验证方式。')
h('2.3 多目标跟踪与事件关联',2)
para('行人跟踪用于维护连续画面中的轨迹标识。Wojke等在SORT中引入深度外观关联度量，改善遮挡条件下的身份连续性[9]。Zhang等提出ByteTrack，通过分阶段关联高、低置信度检测框，减少直接丢弃低分目标造成的轨迹中断[10]。轨迹连续性并不等于事件归属正确。在多人相邻或交叉时，仍需检查香烟离手前与具体手部的持续关系。本文因而区分行人跟踪和人—物关联，前者维护轨迹，后者验证事件来源。')

h('3 方法')
h('3.1 方法总体流程',2)
para('系统以连续视频帧为输入，依次完成目标检测、行人跟踪、人—物关联和时序判断。原始视频同步写入缓冲区；状态机产生候选事件后，证据模块提取关键帧与前后片段，后端完成校验、存储和展示。图1给出模块间关系。')
draw_flow(ASSETS/'pipeline.png');fig(ASSETS/'pipeline.png','图1 目标检测与时序证据链处理流程')
para('第t帧检测结果表示为：')
eq(seq(sub('D','t'),' = {(',ss('b','i','t'),', ',ss('c','i','t'),', ',ss('p','i','t'),') | i = 1, …, ',sub('N','t'),'}'),1)
para('式中，Nₜ为目标数量，b、c、p分别表示边界框、类别和置信度，下标i为目标索引，上标t为帧索引。各帧携带摄像头编号和视频时间戳；检测框统一映射回原图坐标，保证位置、轨迹和视频可以对齐。')
h('3.2 基于YOLOv8n的多类别目标检测',2)
para('检测模块采用已训练的YOLOv8n权重，联合输出香烟、手部和行人。网络通过多尺度特征提取与融合支持不同尺寸目标定位。边界框分布建模的理论基础可追溯至Li等提出的分布焦点损失，该方法用离散概率表达连续边界位置[11]。本文不将使用既有结构或损失函数作为算法创新，现阶段检测实验以基线模型为依据。')
para('设香烟框与手部框分别为b_c和b_h，采用香烟框被手部框覆盖的比例描述局部关系：')
eq(seq(sub('r','ch'),' = ',frac(seq('|',sub('b','c'),' ∩ ',sub('b','h'),'|'),seq('|',sub('b','c'),'|'))),2)
para('式中，竖线表示面积。相比以两框并集面积作分母，该比例减少了香烟框远小于手部框时的面积尺度影响。该指标仅筛选候选关系，需结合持续时间与行人一致性判断持烟；无有效香烟框时不计算该值。')
h('3.3 三段式行为证据链状态机',2)
para('状态机包含空闲、持烟、抛掷和落地四种状态，后三者组成事件证据链。状态按时间顺序推进，对观测不足、关联冲突或超时的记录保留不确定性，状态关系如图2所示。')
draw_flow(ASSETS/'states.png',True);fig(ASSETS/'states.png','图2 三段式行为证据链状态转换')
para('（1）持烟阶段。香烟覆盖比例达到阈值θ_h，且关联同一行人的有效观测连续成立时，累计持烟时间：')
eq(seq(sub('T','h'),' = t − ',ss('t','h','0')),3)
para('式中，t为当前视频时间，t_h⁰为本次连续有效观测的起点。当T_h达到阈值τ_h时建立持烟证据。缺失帧不计为有效持续观测；超过容许缺失间隔则重置，防止长时间遮挡被误算为持续持烟。')
para('（2）抛掷阶段。持烟成立后，监测香烟与手部的分离及其运动变化。设相邻有效观测的香烟中心为q_t和q_prev，平均速度为：')
eq(seq(sub('v','t'),' = ',frac(seq('‖',sub('q','t'),' − ',sub('q','prev'),'‖₂'),'Δt')),4)
para('式中，Δt为观测时间间隔。局部运动分析可采用Lucas–Kanade方法，其利用图像空间梯度进行迭代配准，为局部位移估计提供依据[12]。本方案将光流限制在候选目标邻域内，并检查有效特征点与跟踪误差；无法可靠估计时标记运动证据不足，不以背景或手部运动替代香烟运动。')
para('轨迹点充足时，可用二次函数拟合纵向位置变化，作为辅助一致性约束：')
eq(seq('ŷ(t) = a',sup(seq('(t − ',sub('t','0'),')'),'2'),' + b(t − ',sub('t','0'),') + c'),5)
para('式中，a、b、c为拟合系数，t₀为轨迹起点。拟合不作为所有事件的硬性门槛，以兼顾透视投影、竖直掉落和短轨迹。抛掷候选需同时满足手—烟分离与有效运动观测，单次目标消失不能触发确认。')
para('（3）落地阶段。为每个摄像头标定地面感兴趣区域，并排除允许投放的收集容器。目标进入地面区域后，计算窗口内最大位置偏移：')
eq(seq(sub('d','t'),' = ',sub('max','k ∈ Wₜ'),' ‖',sub('q','k'),' − ',sub('q̄','Wₜ'),'‖₂'),6)
para('式中，Wₜ为观测窗口，q̄_Wₜ为窗口内目标中心均值。位置偏移小于θ_s且有效静止时间达到τ_s时，形成落地证据。三阶段完整且关联一致后输出候选乱扔事件；落地目标无法持续检出时不强行补全证据。相机移动或地面区域配置失效时，应暂停相关判定并重新标定。')
h('3.4 基于行人轨迹的事件关联',2)
para('行人轨迹用于组织持烟历史。手部检测框先依据包含关系与距离分配给行人，再将香烟与对应手部匹配；多人重叠时保留多个候选，不仅依靠抛掷瞬间的最近距离。设抛掷起点为q₀，第j名候选行人的手部中心为h_j，行人框高度为H_j，则归一化距离为：')
eq(seq(sub('d','j'),' = ',frac(seq('‖',sub('q','0'),' − ',sub('h','j'),'‖₂'),sub('H','j'))),7)
para('以行人框高度归一化用于减小远近尺度差异，不代表真实物理距离。统计抛掷前窗口内候选行人与该香烟保持有效持烟关系的比例r_j，定义匹配代价：')
eq(seq(sub('C','j'),' = λ',sub('d','j'),' + (1 − λ)(1 − ',sub('r','j'),')'),8)
para('式中，λ为权重，取值0至1。候选先通过空间门限和时间一致性筛选，再比较代价；最优与次优候选差异不足时，事件保持未关联。多目标分配应满足同一时刻单个香烟对应至多一个行人，避免重复归属。各阈值与权重在验证视频上确定，再固定用于独立测试。')

h('4 实验设计与结果分析')
h('4.1 数据集与实验设置',2)
para('根据现有实验记录，数据集包含香烟、手部和行人三类，共5693张图像。训练集4554张、验证集1139张，约为8∶2，未单独划分测试集。训练集和验证集分别包含8226与2043个实例，分布见表1。本节仅报告已有验证集结果，不将其解释为独立测试性能。')
table('表1 数据集及实例分布',['划分','图像数','香烟','手部','行人','实例总数'],[['训练集',4554,2622,3144,2460,8226],['验证集',1139,869,362,812,2043],['合计',5693,3491,3506,3272,10269]])
para('基线模型加载YOLOv8n预训练权重，输入尺寸为640×640，训练100轮，批量大小8；使用SGD优化器，初始学习率0.01、动量0.937、权重衰减0.0005。训练启用混合精度，最后10轮关闭Mosaic。实验记录报告模型参数量约3.0M、计算量8.1 GFLOPs；这些复杂度值不包含跟踪、光流及视频处理。')
para('检测评价借鉴COCO基准对目标定位与类别识别的评估思路[13]，报告精确率、召回率、mAP50和mAP50–95。精确率与召回率分别为：')
eq(seq('P = ',frac('TP','TP + FP')),9)
eq(seq('R = ',frac('TP','TP + FN')),10)
para('式中，TP、FP、FN分别为按类别和定位匹配条件统计的正确检测、错误检测及漏检。mAP50对应交并比0.50；mAP50–95对0.50至0.95、步长0.05的十个定位阈值取均值。本文没有使用COCO图像进行所报告实验，该文献仅用于说明评价背景。')
para('原始采集来源、标注质检记录和按视频或场景隔离的数据划分清单尚不完整，无法排除相邻帧跨集合造成的信息泄漏；训练硬件及完整软件版本也需由原训练日志补齐。这些限制影响结果的可复现性与外推解释。')
h('4.2 目标检测性能与消融实验',2)
table('表2 YOLOv8n验证集检测结果',['类别','P/%','R/%','mAP50/%','mAP50–95/%'],[['香烟',86.1,76.2,82.2,42.7],['手部',87.5,81.4,88.5,62.4],['行人',85.9,69.6,82.5,52.2],['总体',86.5,75.7,84.4,52.4]],[3.0,2.6,2.6,3.6,4.4])
para('表2显示，手部mAP50最高，为88.5%；香烟mAP50–95为42.7%，低于另外两类，表明更严格定位条件下仍有优化空间。行人召回率为69.6%，提示漏检可能影响轨迹维护，但不能直接据此计算ID切换或事件关联准确率。总体指标采用原验证记录，不由表中已舍入的类别数值重新计算。')
para('消融实验拟设置四组：A为原始YOLOv8n，B增加浅层检测头，C在B上增加注意力，D进一步加入图像增强。表3列出配置及当前证据状态。B至D为后续实验方案，不属于当前已验证模型；图像增强的具体算法、训练或推理阶段以及参数需随代码版本记录。')
table('表3 检测消融实验配置与证据状态',['组别','配置','当前状态'],[['A','原始YOLOv8n','已有基线验证记录'],['B','A＋浅层检测头','未提供对应训练与验证结果'],['C','B＋注意力模块','未提供对应训练与验证结果'],['D','C＋图像增强','未提供对应训练与验证结果']],[1.3,7.4,7.5])
para('各组应采用同一划分、训练预算与评价代码，记录随机种子，在独立测试集上比较总体和香烟类别的性能，并同步报告复杂度与速度。仅比较不同训练设置产生的最优单次结果，无法可靠归因于新增模块。现阶段不报告改进幅度。')
h('4.3 三段式时序验证效果',2)
para('时序验证拟比较三种方案：仅单帧检测、检测加持烟判断，以及检测加跟踪与完整三段式状态机。三组共用检测权重和测试视频，分别检验时间约束和阶段完整性的作用。测试需覆盖真实乱扔、正常持烟、吸烟、投入收集容器及遮挡等情形，并标注事件起止时间。')
para('三种方案均需预先固定“检测结果转为报警”的规则，并采用同一报警合并时间窗。单帧方案不使用跨帧行为特征，报警合并仅用于避免重复计数。按事件进行一对一时间匹配后，计算事件级P、R及F1：')
eq(seq('F1 = ',frac('2PR','P + R')),11)
para('这里P和R为事件指标，与表2的目标检测指标不同。误报另外报告每小时错误报警次数，同时给出测试总时长和正常片段构成。当前尚无带事件真值的视频对比结果，不能宣称三段式状态机已经降低误报或提升召回。')
h('4.4 行人关联准确性评估',2)
para('拟比较仅空间匹配和时空联合匹配，两种方案共用检测与跟踪结果。人工标注需提供跨帧行人身份及每个可评价事件的对应行人。借鉴CLEAR MOT对身份连续性错误的评价思想，统计ID切换次数，并明确逐帧匹配门限与遮挡处理规则[14]。')
para('事件关联准确率定义为：')
eq(seq(sub('A','assoc'),' = ',frac(sub('N','correct'),sub('N','eval'))),12)
para('式中，N_correct为正确关联事件数，N_eval为具有明确行人真值的可评价事件总数，未匹配和错误匹配均计为失败。为避免混淆“关联模块准确率”和“系统事件检出率”，两种方案应接收相同事件输入；完整系统另报告漏检事件。')
para('ID切换次数受视频时长、人数和检测质量影响，不宜单独使用。HOTA将检测和关联纳入统一评价，并可分解分析不同错误来源，可作为补充跟踪指标[15]。当前未提供身份标注与关联输出，因此不报告相关数值，也不以图像检测mAP替代跟踪效果。')
h('4.5 综合分析',2)
para('已有结果支持三类目标检测的基础可行性，但完整行为判断仍有三项限制：香烟离手及落地后的可见性尚未独立验证；验证集未形成独立跨场景测试；多人关联与完整管道性能尚无实测记录。后续应按检测漏失、轨迹断裂、关联错误和状态误触发分类整理失败案例，而非只给出总体准确率。')
para('阈值敏感性分析应在验证视频上分别调整持烟持续时间、运动门限和落地稳定时间，固定其余参数，报告事件精确率与召回率变化。最终参数冻结后再测试，避免根据测试结果反复调参。夜间模糊、相机抖动和多人遮挡仅作为需要覆盖的验证条件，不预先声称系统已具备相应鲁棒性。')

h('5 算法实现与验证')
h('5.1 算法实现环境',2)
para('现阶段已具备目标检测权重、训练配置及前端原型，完整算法管道与后端联调尚未完成验证。实施方案采用Python组织算法，OpenCV处理视频，FastAPI提供事件接口；各模块版本、运行设备与计算精度纳入实验记录。前端已有页面展示不能作为接口已接通或业务已闭环的证据。')
para('模型检测与整条管道测试应固定输入分辨率、批量大小、计算精度与硬件环境，并分别记录摄像头原始帧率、算法实际处理帧率和丢帧比例。离线批处理性能与在线单帧处理性能分开报告。')
h('5.2 算法管道设计',2)
para('视频输入分为处理与证据缓存两条路径。处理路径依次执行目标检测、行人跟踪、人—物关联、局部运动分析和状态更新；缓存路径保存原始视频及时间索引。状态机确认候选后，采集模块读取前置片段并继续收集后续画面，再生成证据文件。证据窗口以事件时间为中心，并覆盖持烟起点至落地终点，避免固定片段截断行为。')
para('视频编码和上传采用异步任务，事件先进入证据生成状态，待文件完整后才进入可复核状态。队列积压、重试和失败分别记录，后端依据事件编号去重。算法输出与证据任务以事件编号关联，便于查询处理进度和定位失败原因。')
h('5.3 模块间数据流设计',2)
table('表4 模块间数据传递',['数据类型','主要字段','用途'],[['视频帧','摄像头、会话、帧编号、时间戳','对齐原始画面'],['检测结果','类别、边界框、置信度','提供目标位置'],['跟踪结果','轨迹编号、行人框、有效状态','维护行人连续性'],['关联记录','人—手—烟对应、匹配代价','建立人—物关系'],['状态记录','阶段、阶段时间、轨迹、关键帧索引','推进时序判断'],['事件记录','事件编号、证据路径、处理状态','查询与复核']],[2.6,8.0,5.6])
para('边界框在进入关联前映射回原图坐标，运动计算使用视频时间戳，运行效率使用单调时钟，两者用途分开。行人编号与摄像头、视频会话共同组成轨迹键，避免不同视频的编号冲突。未确认事件保留具体失败原因，便于追溯到检测、关联或状态判断模块。')
h('5.4 验证流程与效率评价',2)
para('功能验证检查检测框、轨迹、状态转换和视频是否对应，并覆盖目标丢失、遮挡及关联不确定情形。效率评价区分算法管道和端到端链路：前者包含预处理、检测及后处理、跟踪、关联、光流和状态机；后者进一步包含解码、传输和排队开销。证据编码与上传延迟单独统计。')
para('第i帧进入管道及完成状态更新的时刻分别为t_in,i与t_out,i，耗时为：')
eq(seq(sub('T','i'),' = 1000 × (',sub('t','out,i'),' − ',sub('t','in,i'),')'),13)
para('时间戳单位为秒，T_i单位为毫秒。处理N帧的平均耗时为：')
eq(seq(sub('T','avg'),' = ',frac(seq(sub('T','1'),' + ',sub('T','2'),' + … + ',sub('T','N')),'N')),14)
para('按实际完成帧数与测量区间计算吞吐率：')
eq(seq('FPS = ',frac('N',sub('ΔT','wall'))),15)
para('式中，ΔT_wall为测量区间的实际时长，单位为秒。存在并行和排队时，FPS与平均单帧延迟分别测量，不直接互取倒数。测试先预热，GPU计时等待相应任务完成，同时报告均值、95百分位耗时、处理帧率和丢帧情况。')
para('现有实验记录中的约2.6 ms为GPU批处理条件下的单帧检测推理耗时，不包含跟踪、光流、状态判断及视频处理。因未提供完整运行日志，本研究不据此换算系统FPS，也不宣称已满足多路在线监测要求。')

h('6 应用前景与推广')
h('6.1 应用场景与部署条件',2)
para('系统可面向校园出入口、步行道路等固定视角场所开展小范围试点。部署前需检查香烟在持烟、离手和落地阶段的像素尺寸与清晰度，并标定地面和允许投放区域。现有摄像头是否可复用取决于分辨率、距离、视角、压缩率及算力条件，不能预先认定无需新增硬件。')
para('试点宜先采用离线视频回放核对，再开展在线候选告警。人工复核通过的事件可按时间和区域汇总，供清理安排与巡查调整使用；证据不完整的记录保留为线索。异常事件的识别结果不应直接等同于责任认定。')
h('6.2 隐私保护与数据管理',2)
para('方案以视频内的临时轨迹编号关联事件，不以人脸识别或真实身份识别为必要功能。原始证据与日常展示分开管理，普通展示采用面部等敏感区域遮挡；原始片段仅向获授权人员开放，设置保存期限、访问记录及删除机制。')
para('采集范围限定于业务所需区域，事件证据按最小必要原则保存，避免长期保留无关行人视频。具体部署需结合场地管理规则、采集目的和适用要求另行评估。本节描述拟采用的数据保护措施，不将方案设计等同于已经完成合规审查。')
h('6.3 成本效益与推广边界',2)
para('成本评价需同时考虑摄像头适配、计算设备、存储、维护及人工复核。潜在收益主要来自缩短事件检索时间、辅助安排清理和发现重复发生区域，但误报也会增加复核负担。应在试点中记录每小时告警数、人工核查耗时、清理响应时间及运行费用，再与原有方式比较。')
para('目前未开展现场成本对照，因此不报告节省比例或经济收益。只有在事件识别与证据完整性达到场景要求，且复核工作量可接受后，才适合扩大摄像头数量。不同场景的部署应重新评估阈值、遮挡和照明条件，避免将单一验证集性能直接推广至全域监测。')

h('7 结论')
para('本文围绕烟头乱扔监测，给出目标检测、行人关联、三段式状态判断及证据归档的系统方案。已有验证记录显示，YOLOv8n在1139张图像上的总体mAP50为84.4%、mAP50–95为52.4%，香烟类别mAP50为82.2%，为后续视频分析提供了检测基础。')
para('当前证据尚不足以证明完整乱扔识别、行人归属及实时处理效果。后续重点是补充独立视频与身份标注，完成检测消融、时序对比及整条管道测速，并在实际场景中评估漏检、误报和复核负担。只有通过这些验证，才能进一步判断该方案的应用范围及实际效益。')

refs=[
('SLAUGHTER E, GERSBERG R M, WATANABE K, et al. Toxicity of cigarette butts, and their chemical components, to marine and freshwater fish[J]. Tobacco Control, 2011, 20(Suppl 1): i25–i29. DOI: 10.1136/tc.2010.040170.','https://pubmed.ncbi.nlm.nih.gov/21504921/'),
('REDMON J, DIVVALA S, GIRSHICK R, et al. You Only Look Once: Unified, Real-Time Object Detection[C]//Proceedings of CVPR. 2016: 779–788. DOI: 10.1109/CVPR.2016.91.','https://www.cv-foundation.org/openaccess/content_cvpr_2016/papers/Redmon_You_Only_Look_CVPR_2016_paper.pdf'),
('LIN T Y, DOLLÁR P, GIRSHICK R, et al. Feature Pyramid Networks for Object Detection[C]//Proceedings of CVPR. 2017: 2117–2125.','https://arxiv.org/abs/1612.03144'),
('WOO S, PARK J, LEE J Y, et al. CBAM: Convolutional Block Attention Module[C]//Proceedings of ECCV. 2018: 3–19.','https://www.ecva.net/papers/eccv_2018/papers_ECCV/html/Sanghyun_Woo_Convolutional_Block_Attention_ECCV_2018_paper.php'),
('WANG Z, LEI L, SHI P. Smoking behavior detection algorithm based on YOLOv8-MNC[J]. Frontiers in Computational Neuroscience, 2023, 17: 1243779. DOI: 10.3389/fncom.2023.1243779.','https://www.frontiersin.org/journals/computational-neuroscience/articles/10.3389/fncom.2023.1243779/full'),
('BAE K, YUN K, KIM H I, et al. Anti-Litter Surveillance based on Person Understanding via Multi-Task Learning[C]//Proceedings of BMVC. 2020.','https://www.bmva-archive.org.uk/bmvc/2020/assets/papers/0279.pdf'),
('KONDRATYUK D, YUAN L, LI Y, et al. MoViNets: Mobile Video Networks for Efficient Video Recognition[C]//Proceedings of CVPR. 2021: 16020–16030.','https://openaccess.thecvf.com/content/CVPR2021/html/Kondratyuk_MoViNets_Mobile_Video_Networks_for_Efficient_Video_Recognition_CVPR_2021_paper.html'),
('ALHARBI E, ALSULAMI G, ALJOHANI S, et al. Real-time detection and monitoring of public littering behavior using deep learning for a sustainable environment[J]. Scientific Reports, 2025, 15: 3000. DOI: 10.1038/s41598-024-77118-x.','https://pubmed.ncbi.nlm.nih.gov/39848984/'),
('WOJKE N, BEWLEY A, PAULUS D. Simple Online and Realtime Tracking with a Deep Association Metric[C]//Proceedings of ICIP. 2017: 3645–3649. DOI: 10.1109/ICIP.2017.8296962.','https://arxiv.org/abs/1703.07402'),
('ZHANG Y, SUN P, JIANG Y, et al. ByteTrack: Multi-Object Tracking by Associating Every Detection Box[C]//Proceedings of ECCV. 2022: 1–21.','https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136820001.pdf'),
('LI X, WANG W, WU L, et al. Generalized Focal Loss: Learning Qualified and Distributed Bounding Boxes for Dense Object Detection[C]//Advances in Neural Information Processing Systems. 2020, 33: 21002–21012.','https://proceedings.nips.cc/paper_files/paper/2020/hash/f0bda020d2470f2e74990a07a607ebd9-Abstract.html'),
('LUCAS B D, KANADE T. An Iterative Image Registration Technique with an Application to Stereo Vision[C]//Proceedings of IJCAI. 1981, 2: 674–679.','https://publications.ri.cmu.edu/an-iterative-image-registration-technique-with-an-application-to-stereo-vision-ijcai'),
('LIN T Y, MAIRE M, BELONGIE S, et al. Microsoft COCO: Common Objects in Context[C]//Proceedings of ECCV. 2014: 740–755.','https://www.microsoft.com/en-us/research/wp-content/uploads/2014/09/LinECCV14coco.pdf'),
('BERNARDIN K, STIEFELHAGEN R. Evaluating Multiple Object Tracking Performance: The CLEAR MOT Metrics[J]. EURASIP Journal on Image and Video Processing, 2008: 246309. DOI: 10.1155/2008/246309.','https://link.springer.com/article/10.1155/2008/246309'),
('LUITEN J, OŠEP A, DENDORFER P, et al. HOTA: A Higher Order Metric for Evaluating Multi-object Tracking[J]. International Journal of Computer Vision, 2021, 129: 548–578. DOI: 10.1007/s11263-020-01375-2.','https://link.springer.com/article/10.1007/s11263-020-01375-2')]
assert citations==list(range(1,16)),citations
h('参考文献')
doc.paragraphs[-1].paragraph_format.page_break_before=True
for i,(text,url) in enumerate(refs,1):
    p=doc.add_paragraph()
    p.paragraph_format.first_line_indent=Pt(-18)
    p.paragraph_format.left_indent=Pt(18)
    p.paragraph_format.line_spacing=1.12
    p.paragraph_format.space_after=Pt(5)
    p.paragraph_format.keep_together=True
    # The reference itself links to its original source, with no extra visible label.
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    rid=p.part.relate_to(url,RT.HYPERLINK,is_external=True)
    link=OxmlElement('w:hyperlink');link.set(qn('r:id'),rid)
    r=OxmlElement('w:r');rp=OxmlElement('w:rPr');co=OxmlElement('w:color');co.set(qn('w:val'),'000000');rp.append(co)
    sz=OxmlElement('w:sz');sz.set(qn('w:val'),'18');rp.append(sz);r.append(rp)
    te=OxmlElement('w:t');te.text=f'[{i}] {text}';r.append(te);link.append(r);p._p.append(link)

footer=sec.footer.paragraphs[0]
footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
footer.paragraph_format.first_line_indent=Pt(0)
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)

path=OUT/'烟头乱扔行为监测论文_完整初稿.docx'
# Remove the default template's decorative title border and style-linked colors.
for tree in [doc.styles.element,doc.element]:
    for node in list(tree.xpath('.//w:pBdr')):
        node.getparent().remove(node)
doc.save(path)
manifest={'title':doc.core_properties.title,'citation_order':citations,'reference_count':len(refs),'equation_count':15,'references':[{'id':i,'text':t,'url':u,'human_verification':'pending'} for i,(t,u) in enumerate(refs,1)],'status':'draft_not_submission_ready','missing':['独立视频事件和行人ID标注','A—D消融实验','状态机与关联对比','整条流水线测速','作者单位与基金信息','完整原始训练环境及日志'],'result_source':'用户提供的烟踪智治_实验部分_公式与理论及图表(1).docx','notes':'训练统计与性能按用户文档转录，未重新运行验证；时序及关联是设计方案；图为原创流程示意。'}
(ROOT/'audit.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(path)
print('citations:',citations,'display equations:',15,'all native math objects:',len(doc.element.xpath('//m:oMath')))
print('characters:',sum(len(p.text) for p in doc.paragraphs))
