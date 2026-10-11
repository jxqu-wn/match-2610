import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from embedding_classifier import LocalEncoder, internal_split, metrics, nearest_predict, resolve_runtime


class EmbeddingClassifierTests(unittest.TestCase):
    def test_runtime_cpu_and_auto_quantization(self):
        with patch('torch.cuda.is_available', return_value=True):
            device, dtype = resolve_runtime('auto', 'auto', True)
        self.assertEqual(str(device), 'cpu')
        self.assertEqual(dtype, 'float32')
        with self.assertRaises(ValueError):
            resolve_runtime('cpu', 'float16', False)

    def test_cuda_selection_and_errors(self):
        with patch('torch.cuda.is_available', return_value=True), \
             patch('torch.cuda.device_count', return_value=2), \
             patch('torch.cuda.current_device', return_value=1):
            device, dtype = resolve_runtime('auto', 'auto', False)
            self.assertEqual(str(device), 'cuda:1')
            self.assertEqual(dtype, 'float16')
            with self.assertRaises(ValueError):
                resolve_runtime('cuda:2', 'auto', False)
            with self.assertRaises(ValueError):
                resolve_runtime('cuda:0', 'auto', True)
        with patch('torch.cuda.is_available', return_value=False):
            self.assertEqual(str(resolve_runtime('auto', 'auto', False)[0]), 'cpu')
            with self.assertRaises(ValueError):
                resolve_runtime('cuda', 'auto', False)

    def test_internal_split_excludes_duplicate_dev_texts(self):
        rows = [dict(question='重复问题', db='MYSQL') for _ in range(10)]
        rows += [dict(question=f'船舶问题{i}', db='POSTGRESQL') for i in range(20)]
        fit, dev = internal_split(rows)
        self.assertFalse({rows[i]['question'] for i in fit} &
                         {rows[i]['question'] for i in dev})
        self.assertTrue(fit)
        self.assertTrue(dev)

    def test_nearest_preserves_multidatabase_labels(self):
        train = np.array([[1., 0.], [0., 1.]])
        result = nearest_predict(train, ['MYSQL', 'MYSQL|POSTGRESQL'],
                                 np.array([[0.1, 0.99]]))
        self.assertEqual(result.tolist(), ['MYSQL|POSTGRESQL'])

    def test_metrics_distinguish_engine_and_type_errors(self):
        rows = [dict(db='MYSQL'), dict(db1='MYSQL', db2='POSTGRESQL')]
        result = metrics(rows, ['SQLite', 'MYSQL|POSTGRESQL'])
        self.assertEqual(result['database_set_accuracy'], 0.5)
        self.assertEqual(result['single_multi_accuracy'], 1.0)

    def test_cache_roundtrip_and_settings_invalidation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = root / 'model'
            model.mkdir()
            for name in ('model.safetensors', 'tokenizer.json', 'config.json'):
                (model/name).write_text('fixture')
            encoder = LocalEncoder(model, root/'cache')
            encoder.cache['问题'] = np.array([0.6, 0.8], dtype=np.float32)
            encoder._save()
            restored = LocalEncoder(model, root/'cache')
            np.testing.assert_allclose(restored.encode(['问题']), [[0.6, 0.8]])
            different = LocalEncoder(model, root/'cache', max_length=128)
            self.assertNotEqual(restored.cache_path, different.cache_path)
            self.assertEqual(different.cache, {})
            with patch('torch.cuda.is_available', return_value=True), \
                 patch('torch.cuda.device_count', return_value=1):
                gpu = LocalEncoder(model, root/'cache', device='cuda:0')
                full = LocalEncoder(model, root/'cache', device='cuda:0', dtype='float32')
            self.assertNotEqual(restored.cache_path, gpu.cache_path)
            self.assertNotEqual(full.cache_path, gpu.cache_path)
            self.assertEqual(gpu.signature['dtype'], 'float16')


if __name__ == '__main__':
    unittest.main()
