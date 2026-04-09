# 需求文档：RAG代码生成系统

## 简介

本文档定义了基于检索增强生成（RAG）的代码生成系统的功能和非功能需求。该系统旨在为开发者提供高质量的代码生成服务，通过智能检索和大语言模型相结合的方式，在单机环境下实现最优的代码生成质量。

## 术语表

- **System**: RAG代码生成系统的整体
- **Query_Rewriter**: Query重写模块，负责理解和优化用户输入
- **Retriever**: 多阶段检索器，负责从知识库检索相关代码
- **Prompt_Constructor**: Prompt构造器，负责组装最终输入
- **Code_Generator**: 代码生成器，负责调用LLM生成代码
- **Knowledge_Base**: 代码知识库，存储高质量代码片段
- **Cache_Manager**: 缓存管理器，负责查询结果缓存
- **Valid_Query**: 非空且长度在合理范围内的用户输入
- **Code_Snippet**: 代码片段，包含代码内容、摘要、质量分数等元数据
- **Retrieval_Result**: 检索结果，包含代码片段和相关性分数
- **Quality_Score**: 代码质量分数，范围为0-10

## 需求

### 需求1：用户查询处理

**用户故事：** 作为开发者，我希望能够用自然语言描述我的代码需求，系统能够理解并生成相应的代码，从而提高我的开发效率。

#### 验收标准

1. WHEN 用户提交一个有效查询 THEN THE Query_Rewriter SHALL 标准化该查询并扩展相关关键词
2. WHEN 用户提交空查询或仅包含空白字符的查询 THEN THE System SHALL 拒绝该请求并返回错误信息
3. WHEN 用户提交超过1000字符的查询 THEN THE System SHALL 拒绝该请求并返回错误信息
4. WHEN Query重写完成 THEN THE Query_Rewriter SHALL 返回包含原始查询、重写后查询和扩展关键词的上下文对象

### 需求2：多阶段代码检索

**用户故事：** 作为系统，我需要从代码知识库中检索最相关的代码片段，以便为代码生成提供高质量的参考上下文。

#### 验收标准

1. WHEN 接收到有效的查询上下文 THEN THE Retriever SHALL 并行执行向量检索和关键词检索
2. WHEN 向量检索执行时 THEN THE Retriever SHALL 返回语义相似度最高的前10个代码片段
3. WHEN 关键词检索执行时 THEN THE Retriever SHALL 返回关键词匹配度最高的前10个代码片段
4. WHEN 两路检索完成后 THEN THE Retriever SHALL 使用RRF算法融合检索结果
5. WHEN RRF融合完成后 THEN THE Retriever SHALL 使用Reranker模型对候选结果进行精排序
6. WHEN 精排序完成后 THEN THE Retriever SHALL 结合质量分数和GitHub stars进行加权排序
7. WHEN 最终排序完成后 THEN THE Retriever SHALL 返回分数最高的Top-K个结果

### 需求3：检索结果质量保证

**用户故事：** 作为系统，我需要确保检索结果的质量和一致性，以便生成高质量的代码。

#### 验收标准

1. THE Retriever SHALL 确保返回的结果数量不超过请求的top_k参数
2. THE Retriever SHALL 确保所有检索结果按分数降序排列
3. THE Retriever SHALL 确保所有检索结果的分数在0到1的范围内
4. WHEN 知识库为空或无相关结果时 THEN THE Retriever SHALL 返回空列表

### 需求4：Prompt构造与Token管理

**用户故事：** 作为系统，我需要将检索到的代码片段和用户查询组装成高质量的Prompt，同时确保不超过模型的上下文长度限制。

#### 验收标准

1. WHEN 接收到用户查询和检索结果 THEN THE Prompt_Constructor SHALL 构造包含系统指令、参考代码和用户问题的完整Prompt
2. THE Prompt_Constructor SHALL 确保构造的Prompt总token数不超过配置的最大值
3. WHEN 检索结果为空时 THEN THE Prompt_Constructor SHALL 仍然返回包含系统指令和用户问题的有效Prompt
4. WHEN 代码片段总token数超过预算时 THEN THE Prompt_Constructor SHALL 按分数优先级选择代码片段直到达到token预算上限

### 需求5：代码生成

**用户故事：** 作为开发者，我希望系统能够基于我的需求生成高质量、可运行的代码，从而节省我的开发时间。

#### 验收标准

1. WHEN 接收到有效的Prompt THEN THE Code_Generator SHALL 使用DeepSeekCoder模型生成代码
2. THE Code_Generator SHALL 确保生成的代码token数不超过配置的max_new_tokens参数
3. WHEN 生成温度设置为0时 THEN THE Code_Generator SHALL 对相同输入产生确定性的输出
4. WHEN 生成过程超过30秒 THEN THE System SHALL 终止生成并返回超时错误

### 需求6：查询结果缓存

**用户故事：** 作为用户，我希望相同或相似的查询能够快速返回结果，从而获得更好的使用体验。

#### 验收标准

1. WHEN 缓存功能启用且查询在缓存中存在 THEN THE Cache_Manager SHALL 直接返回缓存的结果
2. WHEN 查询结果生成完成 THEN THE Cache_Manager SHALL 将结果存入缓存
3. WHEN 缓存条目超过有效期 THEN THE Cache_Manager SHALL 自动失效该条目
4. WHEN 缓存大小超过配置的最大值 THEN THE Cache_Manager SHALL 使用LRU策略淘汰最久未使用的条目

### 需求7：性能要求

**用户故事：** 作为用户，我希望系统能够快速响应我的请求，从而保持流畅的开发体验。

#### 验收标准

1. WHEN 查询首次执行时 THEN THE System SHALL 在5秒内返回结果
2. WHEN 查询命中缓存时 THEN THE System SHALL 在100毫秒内返回结果
3. THE System SHALL 确保检索阶段耗时不超过2秒
4. THE System SHALL 确保代码生成阶段耗时不超过3秒
5. THE System SHALL 确保GPU显存占用不超过6GB
6. THE System SHALL 确保系统内存占用不超过8GB

### 需求8：资源管理

**用户故事：** 作为系统管理员，我需要系统能够高效利用有限的硬件资源，确保稳定运行。

#### 验收标准

1. WHEN 系统启动时 THEN THE System SHALL 将DeepSeekCoder模型以4bit量化方式加载到GPU显存
2. THE System SHALL 确保主模型常驻GPU显存以避免重复加载
3. WHEN Reranker模型需要使用时 THEN THE System SHALL 以小批量方式执行推理以控制显存占用
4. THE System SHALL 将FAISS向量索引和BM25索引加载到CPU内存
5. WHERE NPU可用 THEN THE System SHALL 将Embedding模型加载到NPU以减轻GPU负担

### 需求9：错误处理与容错

**用户故事：** 作为用户，我希望系统能够优雅地处理错误情况，并提供清晰的错误信息。

#### 验收标准

1. WHEN 模型文件不存在 THEN THE System SHALL 抛出明确的错误信息并拒绝启动
2. WHEN GPU显存不足 THEN THE System SHALL 提示用户并建议使用更激进的量化方式
3. WHEN 检索无结果时 THEN THE System SHALL 使用仅包含系统指令的Prompt继续生成
4. WHEN 生成过程发生异常 THEN THE System SHALL 记录错误日志并返回友好的错误信息
5. IF 单次请求失败 THEN THE System SHALL 保持可用状态以处理后续请求

### 需求10：安全与访问控制

**用户故事：** 作为系统管理员，我需要保护系统免受恶意使用，确保服务的稳定性和安全性。

#### 验收标准

1. THE System SHALL 对所有用户输入进行验证和清理以防止注入攻击
2. THE System SHALL 扫描生成的代码中的危险模式并添加警告
3. THE System SHALL 实施速率限制以防止资源耗尽攻击
4. WHEN 用户在60秒内发送超过10个请求 THEN THE System SHALL 拒绝后续请求并返回速率限制错误
5. THE System SHALL 记录所有查询和生成结果的审计日志

### 需求11：代码知识库管理

**用户故事：** 作为系统管理员，我需要管理代码知识库的内容，确保其包含高质量的代码片段。

#### 验收标准

1. WHEN 添加新代码片段时 THEN THE Knowledge_Base SHALL 验证其质量分数不低于5.0
2. WHEN 添加新代码片段时 THEN THE Knowledge_Base SHALL 验证其GitHub stars不低于100
3. WHEN 添加新代码片段时 THEN THE Knowledge_Base SHALL 自动生成其向量表示
4. WHEN 添加新代码片段时 THEN THE Knowledge_Base SHALL 自动生成其代码摘要
5. THE Knowledge_Base SHALL 同时更新FAISS向量索引和BM25关键词索引

### 需求12：批量处理能力

**用户故事：** 作为开发者，我希望能够批量提交多个代码生成请求，从而提高处理效率。

#### 验收标准

1. WHEN 接收到批量查询请求 THEN THE System SHALL 依次处理每个查询
2. WHEN 批量处理时 THEN THE System SHALL 复用已加载的模型和索引
3. IF 批量处理中某个查询失败 THEN THE System SHALL 继续处理剩余查询
4. WHEN 批量处理完成 THEN THE System SHALL 返回所有查询的结果列表

### 需求13：监控与可观测性

**用户故事：** 作为系统管理员，我需要监控系统的运行状态和性能指标，以便及时发现和解决问题。

#### 验收标准

1. THE System SHALL 记录每个请求的各阶段耗时
2. THE System SHALL 提供健康检查接口以报告系统状态
3. THE System SHALL 提供性能指标接口以查询统计数据
4. THE System SHALL 记录GPU显存使用率和系统内存使用率
5. WHERE 监控功能启用 THEN THE System SHALL 暴露Prometheus格式的指标端点

### 需求14：配置管理

**用户故事：** 作为系统管理员，我希望能够通过配置文件灵活调整系统参数，而无需修改代码。

#### 验收标准

1. THE System SHALL 支持通过YAML配置文件设置所有关键参数
2. THE System SHALL 在启动时加载并验证配置文件
3. WHEN 配置文件格式错误 THEN THE System SHALL 拒绝启动并提示具体错误
4. THE System SHALL 支持通过环境变量覆盖配置文件中的参数

### 需求15：API接口

**用户故事：** 作为客户端开发者，我需要清晰、稳定的API接口来集成代码生成功能。

#### 验收标准

1. THE System SHALL 提供RESTful API接口用于代码生成
2. THE System SHALL 接受JSON格式的请求并返回JSON格式的响应
3. WHEN API请求成功 THEN THE System SHALL 返回HTTP 200状态码和生成的代码
4. WHEN API请求失败 THEN THE System SHALL 返回适当的HTTP错误状态码和错误描述
5. THE System SHALL 提供API文档以描述所有接口的使用方法
