# 绫度织纹谱峰研究册

绫度纺织测量组的15位谱分析员从独立织片的不等距截面厚度采样寻找空间周期证据，再提出独立补测计划。上游输入 `ld-traverse-1-202611.csv` 等位置/厚度文件，下游是负责人批准的全谱CSV和补测说明。原先的三个问题是把不等距位置强制等距FFT、挑最大峰后误用单频p、把谱峰直接解释为制造原因。

固定seed合成三条独立测线，每条120点：18mm周期、30/12mm多峰、恒厚对照。默认预设201等频网格（周期10–90mm）、B199标签置换。A测线实际选中18mm、最大功率0.933678718814、全网格p=.005；这些是合成数据的研究结果，不是设备参数或现场因果结论。

## 启动与角色

```sh
cp .env.example .env
docker compose up --build -d --wait
docker compose exec -T backend python -m scripts.seed_demo
```

|入口|地址|
|---|---|
|浏览器|http://localhost:18238|
|API / Swagger|http://localhost:19238/docs|
|PostgreSQL16|127.0.0.1:17738|

|账号 / 密码|页面和权限|典型动作|
|---|---|---|
|admin@lingdu.demo / Lingdu2026!|六页、写入、审批|批准或退回独立织片补测|
|analyst@lingdu.demo / Lingdu2026!|六页、导入/修订/计划/运行/说明|冻结网格、真队列；审批403|
|viewer@lingdu.demo / Lingdu2026!|六页只读、批准CSV|阅读全谱/窗口/全局p并导出；写入403|

`.env.example`列出三个端口、POSTGRES_DB/USER/PASSWORD、JWT_SECRET、SEED_DEMO、RATE_LIMIT_WRITES（默认60）。演示密码和JWT secret仅用于本地，部署须设置自己的值。首次启动自动seed，独立重复执行也幂等，不覆盖用户测点和说明。

Compose恰好frontend/backend/worker/db/redis五服务，各有healthcheck。Nginx `/api/`移除前缀后转发FastAPI，前端探针127.0.0.1；backend等DB/Redis，worker再等backend。真实Celery任务保存JSON与数据库结果，后端/worker共享artifacts命名卷。停止清除本题演示数据：`docker compose down -v --remove-orphans`。

## 谱分析员的一天

1. 09:00，林纬打开“谱峰总览”，先区分空间周期证据和制造原因。
2. 在“不等距测线”核对 `LD-34A 十八毫米纹理` / `ld-traverse-1-202611.csv`，如 `LD1-P001` 的位置mm和厚度mm。保留实际间距，不插成等距输入。
3. 导入独立织片JSON或修订厚度；重复位置会拒绝。每条4–240点、跨度≤10000mm，已有任务保留提交时数据快照。
4. 在“频率计划”预先声明周期范围10–90mm：fmin=1/90、fmax=.1、201等频点、B199、seed234。计划冻结后不编辑；看过谱峰才改范围应作为探索新研究，需独立资料核对。
5. 从该测线的冻结计划排队。提交时源点和计划都复制进run，worker只使用这两份快照。
6. A研究120点/201频点，选中18mm、功率.933678718814。全网格null最大值没有达到观测值，p=(0+1)/(199+1)=.005，而不是对挑出的频率报单频p。
7. 读选频率带截距拟合、相对于x₀的幅度/相位、全部谱与采样窗口函数，核对混叠和泄漏。网格间距不是周期置信区间。
8. 在“织片补测”写独立织片来源、保持预设网格和不等距补测位置的行动，不认定织机成因。
9. 方绎批准或退回；苏纾下载批准全谱CSV。重复审批409，事后改点不能改写冻结运行或批准快照；过程留痕保留导入、计划、队列、审阅和导出。

## 数值口径

对每个预设频率f拟合 `y=c+a cos(2πf(x−x₀))+b sin(2πf(x−x₀))`，x₀是首个有序位置。先计算x−x₀再构造相位，避免大绝对坐标进入三角函数。厚度也先减首值再中心化计算RSS0，降低大偏移的小方差消去。

cos/sin列各减其均值形成A，QR分解A=QR。对中心化厚度y_c，解释平方和为`||Qᵀy_c||²`，功率`1−RSSf/RSS0`等价于其除以RSS0，浮点末位裁到[0,1]。回求a/b，再恢复截距c。保存完整频率谱、每频RSS、奇异值、全部排除理由和最佳频率在原位置的拟合/残差。

中心化设计的sigma_min≤1e-10×max(sigma_max,sqrtN)视为秩不足或病态，排除且保存原因；所有频率退化失败。固定x使纳入频率集合对所有置换相同。恒定厚度RSS0=0时功率未定义，明确失败，不伪造零谱。

相位定义为 `c+A cos(2πf(x−x₀)−φ)`，A=hypot(a,b)非负，φ=atan2(b,a)，单位rad，相对于x₀并按atan2主值报告；不是绝对地理相位。x正比例缩放、f反向缩放保持相位与功率。

每个频率的QR只由x决定，整条任务缓存一次。B199–499次固定x打乱y标签，每次仍重新计算完整纳入网格的功率并取最大，保存所有null最大值。`p_global=(1+#nullmax≥observedmax−tol)/(B+1)`，预先tol=1e-12保守计入数值并列；最大峰频率在同tol并列时取较低频率。+1使B199的最小Monte Carlo p=.005。

采样窗口是`|mean(exp(i2πf(x−x₀)))|²`，只由位置决定，用来核对采样结构；它不能消除混叠。默认网格Δf约.00044444444 cycles/mm，不等于周期CI。该全局p只对预先冻结的搜索范围、iid可交换且同方差误差的无周期null解释，不是制造原因、在线诊断或任意后验挑范围的确认检验。

## 实体、界面与校验

79个有职责的Python/TS/TSX/CSS文件（不含空包、依赖和dist）。五实体TraverseStudy → TraversePoint → FrequencyPlan → SpectrumRun → WeaveNote贯穿ORM/schema/service/routes、前端API/store和六页：谱峰总览、不等距测线、频率计划、完整谱与全局p、织片补测、过程留痕。

前端 `src/{api,stores,types,components/common,hooks,pages,router,utils,constants}`；后端 `src/{routes,controllers,services,models,schemas,middlewares,utils,constants,config}`，另scripts/seed_demo.py与migrations/。SpectrumPlot、TracePlot、PeakSummary、RunList在多页复用，PermutationPanel只画后端实际null频数；useTask/useRoute和format处理交互。React挂载id=root与createRoot一致。

Role/RunStatus/NoteStatus位于 `backend/src/constants/enums.py`，前端对应 `frontend/src/constants/enums.ts`。JWT、审计、RequestID/Error/Redis写限流三个中间件形成横切链路。配额按令牌摘要或无令牌IP分钟计数，默认60写请求，429含Retry-After；计数服务不可用503，健康GET不计。审批行锁使draft只能审一次，CSV取冻结result_snapshot。

位置有限且0–1e12、测线跨度≤10000mm；厚度有限且0–1e6；频率严格递增、正且≤1周期/mm，3–401点，计划B199–499。NaN/Inf/bool数值参数、重复位置、错误测线/计划匹配均安全422；错误对象不回显非法input。PG数值列使用Double(asdecimal=False)，真实数据库类型double precision，API保持Python float。

|层|实现|
|---|---|
|前端|React18 / TypeScript / Vite6.4.6，Manrope+Noto Serif SC，靛墨/棉白/黄铜谱峰|
|后端|Python3.11 / FastAPI / SQLAlchemy / PostgreSQL16|
|队列|Celery5.4 / Kombu5.4.2 / Redis7，worker并发1|
|算法|中心坐标QR全谱、全网格标签置换、采样窗口与选频拟合|

本地前端 `cd frontend && npm ci && npm run dev`；`npm run build`执行tsc/Vite。后端安装requirements并设置DATABASE_URL/REDIS_URL/JWT_SECRET后运行uvicorn。当前ORM create_all初始化，migrations只作初始结构说明，不声称生产迁移链。MIT许可证见LICENSE。

实际验收和边界见批次 `test-artifacts/gb-0034/TESTING.md`。关键JSON、CSV、PNG、原始.log、测试脚本和交付哈希都与源码分离。未验证外部真实织片、异方差/相关误差、生产压力或完整无障碍；令牌/IP分钟配额不是生产抗滥用全链路，换登录令牌可获新计数。Google字体断网回退本地字体。恒厚对照、纯18mm16点校验与120点噪声fixture是不同输入，结果不能互相冒充。
