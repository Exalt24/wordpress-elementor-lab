<?php
namespace Opencart\Catalog\Controller\Extension\Seolab\Feed;

require_once DIR_EXTENSION . 'seolab/system/library/markup.php';

use Seolab\Markup;

/** An XML sitemap at /sitemap.xml (the rewrite is in htaccess.extra): the home page, every enabled category and every enabled product. */
class Sitemap extends \Opencart\System\Engine\Controller {
	public function index(): void {
		$language = 'language=' . $this->config->get('config_language');
		$urls = [[$this->config->get('config_url'), '']];

		$this->load->model('catalog/category');
		$this->load->model('catalog/product');

		foreach ($this->model_catalog_category->getCategories(0) as $category) {
			$urls[] = [Markup::canonicalUrl($this->url->link('product/category', $language . '&path=' . $category['category_id'])), ''];
		}

		foreach ($this->model_catalog_product->getProducts(['start' => 0, 'limit' => 5000]) as $product) {
			$urls[] = [Markup::canonicalUrl($this->url->link('product/product', $language . '&product_id=' . $product['product_id'])), $product['date_modified'] ?? ''];
		}

		$this->response->addHeader('Content-Type: application/xml; charset=utf-8');
		$this->response->setOutput(Markup::sitemap($urls));
	}
}
